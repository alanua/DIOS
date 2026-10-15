"""stdlib CI tests: 100 synthetic ops, no CAD program, secrets or live provider."""
import unittest
from dios.provider_capabilities import (CADRequest, CADSession, CapabilityDenied,
    CapabilityRouter, Effect, OperationDescriptor, Profile)
NOW = 2_000_000_000


def fixture(n=100):
    called=[]
    descriptors=tuple(OperationDescriptor(
        operation_id=f"solidworks.parts.feature_{i}", module="parts",
        effect=Effect.READ if i%5==0 else Effect.MUTATE,
        arguments={"value":"number"}, required=frozenset({"value"}),
        since_version="2022") for i in range(n))
    handlers={d.operation_id:(lambda payload, ident=d.operation_id: called.append((ident, payload)))
              for d in descriptors}
    router=CapabilityRouter(provider_id="solidworks.desktop",version="2024",
        licensed_modules=frozenset({"parts"}),descriptors=descriptors,handlers=handlers,
        clock=lambda:NOW, trusted_admission=lambda req, session: True)
    session=CADSession(node_id="node-1",application_id="app-1",workspace_id="toy-1",
        lease_id="lease-1",provider_id="solidworks.desktop",expires_at=NOW+100,
        profile=Profile.FULL_CAD_WORKSPACE)
    def request(op="solidworks.parts.feature_1",value=1):
        return CADRequest("node-1","app-1","toy-1","lease-1","solidworks.desktop",
                          op,{"value":value})
    return router,session,request,called


class RegistryTests(unittest.TestCase):
    def test_unbounded_discovery_catalog_not_fixed_six_operations(self):
        router,session,request,called=fixture(100)
        self.assertEqual(router.public_coverage()["declared"],100)
        self.assertEqual(router.public_coverage()["registered_handlers"],100)
        self.assertEqual(router.public_coverage()["native_bound"],0)
        self.assertEqual(router.public_coverage()["provider_verified"],0)
        for k in (0, 1, 49, 99):
            result=router.execute(request(f"solidworks.parts.feature_{k}"),approved_session=session)
            self.assertEqual(result.status,"IN_PROCESS_HANDLER_CALLED")
        self.assertEqual(len(called),4)

    def test_one_full_workspace_lease_covers_many_operations(self):
        router,session,request,called=fixture(50)
        for i in range(50):
            self.assertEqual(router.execute(request(f"solidworks.parts.feature_{i}"), approved_session=session).status,"IN_PROCESS_HANDLER_CALLED")
        self.assertEqual(len(called),50)

    def test_readonly_denies_mutation_and_allows_read(self):
        router,session,request,called=fixture()
        readonly=CADSession(**{**session.__dict__,"profile":Profile.READ_ONLY})
        self.assertEqual(router.execute(request("solidworks.parts.feature_0"),approved_session=readonly).status,"IN_PROCESS_HANDLER_CALLED")
        with self.assertRaisesRegex(CapabilityDenied,"READ_ONLY_DENIED"):
            router.execute(request("solidworks.parts.feature_1"),approved_session=readonly)
        self.assertEqual(len(called),1)

    def test_exact_bounded_operation(self):
        router,session,request,called=fixture()
        subset=CADSession(**{**session.__dict__,"profile":Profile.BOUNDED,
                            "allowed_operations":frozenset({"solidworks.parts.feature_2"})})
        self.assertEqual(router.execute(request("solidworks.parts.feature_2"),approved_session=subset).status,"IN_PROCESS_HANDLER_CALLED")
        with self.assertRaisesRegex(CapabilityDenied,"BOUNDED_OPERATION_DENIED"):
            router.execute(request("solidworks.parts.feature_1"),approved_session=subset)

    def test_expired_revoked_cross_workspace_provider_deny(self):
        router,session,request,called=fixture()
        for session_kwargs, req in [({"revoked":True},request()),({"expires_at":NOW-1},request()),
           ({}, CADRequest("node-1","app-1","different","lease-1","solidworks.desktop",
                            "solidworks.parts.feature_1",{"value":1})),
           ({}, CADRequest("node-1","app-1","toy-1","lease-1","autocad.desktop",
                            "solidworks.parts.feature_1",{"value":1}))]:
            with self.subTest(kwargs=session_kwargs):
                s=CADSession(**{**session.__dict__,**session_kwargs})
                with self.assertRaises(CapabilityDenied):router.execute(req,approved_session=s)
        self.assertEqual(len(called),0)

    def test_unknown_unbound_and_wrong_args_deny(self):
        router,session,request,called=fixture()
        with self.assertRaisesRegex(CapabilityDenied,"UNKNOWN_PROVIDER_OPERATION"):
            router.execute(request("solidworks.parts.run_shell"),approved_session=session)
        with self.assertRaisesRegex(CapabilityDenied,"ARGUMENT_TYPE_MISMATCH"):
            router.execute(request(value=True),approved_session=session)
        with self.assertRaisesRegex(CapabilityDenied,"NON_JSON_ARGUMENT"):
            router.execute(request(value=float('nan')),approved_session=session)
        with self.assertRaisesRegex(CapabilityDenied,"ARGUMENT_BOUNDARY"):
            c=request()
            bad=CADRequest(*[c.node_id,c.application_id,c.workspace_id,c.lease_id,c.provider_id,c.operation_id],
                           {"value":1,"script":"exec"})
            router.execute(bad,approved_session=session)
        self.assertEqual(len(called),0)

    def test_module_license_version_filter(self):
        desc=(OperationDescriptor("autocad.cam.toolpath","cam",Effect.MUTATE,
                                  since_version="2025"),)
        r=CapabilityRouter(provider_id="autocad.desktop",version="2024",licensed_modules=frozenset(),
                           descriptors=desc,handlers={desc[0].operation_id:lambda x:None},clock=lambda:NOW)
        self.assertEqual(r.public_coverage()["available"],0)
        sess=CADSession("node-1","app-1","toy-1","lease-1","autocad.desktop",NOW+60,Profile.FULL_CAD_WORKSPACE)
        req=CADRequest("node-1","app-1","toy-1","lease-1","autocad.desktop","autocad.cam.toolpath",{})
        with self.assertRaisesRegex(CapabilityDenied,"MODULE_OR_VERSION_UNAVAILABLE"):
            r.execute(req,approved_session=sess)

    def test_untrusted_handler_unbound_fails_closed(self):
        desc=(OperationDescriptor("solidworks.parts.extrude","parts",Effect.MUTATE),)
        r=CapabilityRouter(provider_id="solidworks.desktop",version="2024",licensed_modules=frozenset({"parts"}),
                           descriptors=desc,handlers={},clock=lambda:NOW)
        session=CADSession("node-1","app-1","toy-1","lease-1","solidworks.desktop",NOW+100,Profile.FULL_CAD_WORKSPACE)
        req=CADRequest("node-1","app-1","toy-1","lease-1","solidworks.desktop","solidworks.parts.extrude",{})
        self.assertEqual(r.public_coverage()["registered_handlers"],0)
        with self.assertRaisesRegex(CapabilityDenied,"NATIVE_HANDLER_NOT_REGISTERED"):
            r.execute(req,approved_session=session)

    def test_reject_cross_provider_descriptor(self):
        with self.assertRaisesRegex(CapabilityDenied, "OPERATION_PROVIDER_OR_MODULE_MISMATCH"):
            CapabilityRouter(provider_id="solidworks.desktop",version="2024",
                licensed_modules=frozenset({"parts"}),
                descriptors=(OperationDescriptor("autocad.parts.extrude","parts",Effect.MUTATE),),
                handlers={},clock=lambda:NOW)

    def test_no_external_provider_claim(self):
        r, s, req, c=fixture()
        self.assertNotIn("provider_versions",r.public_coverage())
        self.assertFalse(r.execute(req(),approved_session=s).public()["provider_verified"])

    def test_signed_gate_absent_denies_even_full_workspace(self):
        router, session, request, called = fixture()
        router._trusted_admission = None
        with self.assertRaisesRegex(CapabilityDenied,"TRUSTED_ADMISSION_MISSING"):
            router.execute(request(), approved_session=session)
        self.assertEqual(called, [])

    def test_gate_refusal_and_exception_fail_closed(self):
        router, session, request, called = fixture()
        router._trusted_admission = lambda req, approved: False
        with self.assertRaisesRegex(CapabilityDenied,"TRUSTED_ADMISSION_DENIED"):
            router.execute(request(),approved_session=session)
        def failure(req, approved):
            raise OSError("private internal detail")
        router._trusted_admission = failure
        with self.assertRaisesRegex(CapabilityDenied,"TRUSTED_ADMISSION_UNAVAILABLE") as err:
            router.execute(request(),approved_session=session)
        self.assertNotIn("private internal detail",str(err.exception))
        self.assertEqual(called, [])

    def test_authorized_payload_is_independent_from_original(self):
        called = []
        observed = []
        d=OperationDescriptor("solidworks.parts.assemble","parts",Effect.MUTATE,
                              arguments={"parameters":"object"},required=frozenset({"parameters"}))
        def admission(req, session):
            observed.append(req.arguments["parameters"]["items"][0])
            req.arguments["parameters"]["items"][0] = "tamper"
            return True
        router=CapabilityRouter(provider_id="solidworks.desktop",version="2024",
            licensed_modules=frozenset({"parts"}),descriptors=(d,),
            handlers={d.operation_id:lambda data: called.append(data)},
            trusted_admission=admission,clock=lambda:NOW)
        session=CADSession("node","app","workspace","lease","solidworks.desktop",NOW+100,Profile.FULL_CAD_WORKSPACE)
        input_values={"parameters":{"items":["safe"]}}
        req=CADRequest("node","app","workspace","lease","solidworks.desktop",
            d.operation_id,input_values)
        input_values["parameters"]["items"][0]="changed"
        router.execute(req, approved_session=session)
        self.assertEqual(observed,["safe"])
        self.assertEqual(called[0]["parameters"]["items"],["safe"])

    def test_descriptor_module_mismatch_rejected(self):
        desc=(OperationDescriptor("solidworks.other.inject","parts",Effect.READ),)
        with self.assertRaisesRegex(CapabilityDenied,"OPERATION_PROVIDER_OR_MODULE_MISMATCH"):
            CapabilityRouter(provider_id="solidworks.desktop",version="2024",
                licensed_modules=frozenset({"parts"}),descriptors=desc,handlers={})

    def test_version_components_normalized(self):
        d=OperationDescriptor("solidworks.parts.versioned","parts",Effect.READ,
                              since_version="2024.0",until_version="2024.1")
        self.assertTrue(d.accepts_version("2024"))
        self.assertTrue(d.accepts_version("2024.0.1"))
        self.assertFalse(d.accepts_version("2024.2"))

    def test_no_real_native_functions_reported(self):
        router, _, _, _=fixture(100)
        coverage=router.public_coverage()
        self.assertEqual(coverage["native_bound"],0)
        self.assertEqual(coverage["provider_verified"],0)
        self.assertEqual(coverage["registered_handlers"],100)

    def test_manifest_loads_descriptors_without_dynamic_imports(self):
        manifest={
            "schema":"dios.cad_provider_capabilities.v1",
            "provider_id":"solidworks.desktop",
            "application_version":"2024",
            "modules":["parts"],
            "operations":[{
                "operation_id":"solidworks.parts.extrude", "module":"parts",
                "effect":"MUTATE", "arguments":{"height":"number"},
                "required":["height"], "since_version":"2024",
                "native_transaction_supported":False, "reversible":True,
            }],
        }
        called=[]
        router=CapabilityRouter.from_manifest(
            manifest, handlers={"solidworks.parts.extrude":lambda a: called.append(a)},
            trusted_admission=lambda req, session: True,clock=lambda:NOW,
        )
        session=CADSession("node","app","workspace","lease","solidworks.desktop",NOW+100,Profile.FULL_CAD_WORKSPACE)
        r=CADRequest("node","app","workspace","lease","solidworks.desktop",
                     "solidworks.parts.extrude",{"height":4})
        self.assertEqual(router.execute(r, approved_session=session).status,"IN_PROCESS_HANDLER_CALLED")
        self.assertEqual(called,[{"height":4}])
        self.assertEqual(router.public_coverage()["native_bound"],0)

    def test_manifest_rejects_unknown_fields_and_dynamic_handler(self):
        base={"schema":"dios.cad_provider_capabilities.v1", "provider_id":"solidworks.desktop",
              "application_version":"2024", "modules":["parts"], "operations":[]}
        for changed in ({**base,"__import__":"os"},
                        {**base,"schema":"unknown"},
                        {**base,"modules":["parts","parts"]},
                        {**base,"operations":[{"operation_id":"solidworks.parts.run"}]},
                        {**base,"operations":"not-an-array"}):
            with self.subTest(manifest=changed):
                with self.assertRaises(CapabilityDenied):
                    CapabilityRouter.from_manifest(changed,handlers={})
        router=CapabilityRouter.from_manifest(base,handlers={})
        self.assertEqual(router.public_coverage()["available"],0)

    def test_bad_local_clock_fails_closed(self):
        router, session, request, called = fixture()
        router._clock = lambda: float("nan")
        with self.assertRaisesRegex(CapabilityDenied,"LEASE_REVOKED_OR_EXPIRED"):
            router.execute(request(), approved_session=session)
        self.assertEqual(called,[])

    def test_unhashable_manifest_module_and_required_fail_typed(self):
        base={"schema":"dios.cad_provider_capabilities.v1", "provider_id":"solidworks.desktop",
              "application_version":"2024", "modules":[["parts"]], "operations":[]}
        with self.assertRaisesRegex(CapabilityDenied,"MANIFEST_INVENTORY_INVALID"):
            CapabilityRouter.from_manifest(base, handlers={})
        base["modules"]=["parts"]
        base["operations"]=[{"operation_id":"solidworks.parts.extrude", "module":"parts",
            "effect":"MUTATE", "arguments":{}, "required":[{}],
            "since_version":"2024", "native_transaction_supported":False,"reversible":True}]
        with self.assertRaisesRegex(CapabilityDenied,"MANIFEST_OPERATION_TYPES_INVALID"):
            CapabilityRouter.from_manifest(base, handlers={})

if __name__=="__main__": unittest.main()

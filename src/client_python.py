import sys
from omniORB import CORBA
import CosNaming
from Idls import AuthenticationIDL_idl

def main():
    # 1) ORB init via a corbaloc name‐service URL
    orb = CORBA.ORB_init(
        sys.argv + ['-ORBInitRef', 'NameService=corbaloc::localhost:1050/NameService'],
        CORBA.ORB_ID
    )
    print("ORB object:", orb)
    print("Step 1 completed successfully")

    # 2) Get NameService
    try:
        obj = orb.resolve_initial_references("NameService")
        print("Step 2: resolve_initial_references succeeded")
    except Exception as e:
        print("FAILED at resolve_initial_references:", e)
        sys.exit(1)

    # 3) Narrow to NamingContextExt
    try:
        naming_context = obj._narrow(CosNaming.NamingContextExt)
        print("Step 3: narrowed to NamingContextExt")
        if naming_context is None:
            raise RuntimeError("narrow->NamingContextExt returned None")
    except Exception as e:
        print("FAILED at NamingContextExt narrow:", e)
        sys.exit(1)

    # NEW DEBUGGING: List all bindings in Naming Service
    try:
        print("Listing all bindings in the Naming Service...")
        binding_list, _ = naming_context.list(100)  # Limit to 100 bindings
        for binding in binding_list:
            name = ".".join([n.id for n in binding.binding_name])
            print(" - Found name:", name)
    except Exception as e:
        print("Could not list bindings:", e)

    # 4) Resolve the AuthenticationService
    try:
        auth_obj = naming_context.resolve_str("AuthenticationService")
        print("Step 4: resolved authObj:", auth_obj)
        print("Resolved object type:", type(auth_obj))
    except Exception as e:
        print("FAILED at resolve_str:", e)
        sys.exit(1)

    # 5) Narrow to the typed stub
    authSvc = auth_obj._narrow(
        AuthenticationIDL_idl._0_AuthenticationIDL._objref_AuthenticationService
    )
    if authSvc is None:
        print("FAILED: object is not AuthenticationService")
        sys.exit(1)

    print("Successfully connected to AuthenticationService")

if __name__ == "__main__":
    main()

import sys
from omniORB import CORBA
import CosNaming
from Idls import AuthenticationIDL_idl

def main():
    # 1) ORB init via a corbaloc name‐service URL
    orb = CORBA.ORB_init(
        sys.argv + [
            '-ORBDefaultInitRef',
            'NameService=corbaloc::localhost:2000/NameService'
        ],
        CORBA.ORB_ID
    )
    print("Step 1 completed successfully")

    # 2) Get NameService
    try:
        objRef = orb.resolve_initial_references("NameService")
        print("Step 2: got NameService:", objRef)
    except Exception as e:
        print("FAILED at resolve_initial_references:", e)
        sys.exit(1)

    # 3) Narrow to NamingContextExt
    try:
        ncExt = objRef._narrow(CosNaming.NamingContextExt)
        print("Step 3: narrowed to NamingContextExt")
        if ncExt is None:
            raise RuntimeError("narrow->NamingContextExt returned None")
    except Exception as e:
        print("FAILED at NamingContextExt narrow:", e)
        sys.exit(1)

    # 4) Resolve the AuthenticationService
    try:
        authObj = ncExt.resolve_str("AuthenticationService")
        print("Step 4: resolved authObj:", authObj)
    except Exception as e:
        print("FAILED at resolve_str:", e)
        sys.exit(1)

    # 5) Narrow to the typed stub
    authSvc = authObj._narrow(
        AuthenticationIDL_idl._0_AuthenticationIDL._objref_AuthenticationService
    )
    if authSvc is None:
        print("FAILED: object is not AuthenticationService")
        sys.exit(1)

    print("Successfully connected to AuthenticationService")

if __name__ == "__main__":
    main()
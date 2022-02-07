from libs.csm.csm_interface import CSMApiFactory

if __name__ == "__main__":

    csmrest_obj = CSMApiFactory("rest")
    resp = csmrest_obj.create_payload_for_new_csm_user("valid", "manage")
    print(resp)
    csmgui_obj = CSMApiFactory("gui")
    csmcli_obj = CSMApiFactory("cli")
    
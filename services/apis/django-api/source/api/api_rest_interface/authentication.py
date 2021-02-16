from rest_framework.authentication import TokenAuthentication


class TokenAuthenticationBearer(TokenAuthentication):
    """
    Same as DRFs TokenAuthentication but uses the keyword Bearer instead of
    Token in the request header, mostly because this is the standard
    implemented in OpenAPI.
    """
    keyword = "Bearer"

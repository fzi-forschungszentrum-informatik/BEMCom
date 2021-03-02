# pgAdmin4 Tool 

This is a wrapper around the [pgAdmin4 Docker image](https://hub.docker.com/r/dpage/pgadmin4). The image here adds automatic HTTPs certificate generation.

### ToDo

This image does not support running as arbitrary user


### Configuration

##### Ports

| Port | Usage/Remarks                          |
| ---- | -------------------------------------- |
| 443  | HTTPs port for pgAdmin user interface. |

##### Environment Variables

The most essential settings are these:

| Enironment Variable      | Example  Value                                    | Usage/Remarks                                                |
| ------------------------ | ------------------------------------------------- | ------------------------------------------------------------ |
| SSL_CERT_PEM             | -----BEGIN CERTIFICATE-----<br/>MIIFCTCCAvG...    | The certificate to use for HTTPS. Will generate a self signed certificate if SSL_CERT_PEM or SSL_KEY_PEM are empty. The self signed certificate will make HTTPS work, but browsers will issue a warning. |
| SSL_KEY_PEM              | -----BEGIN PRIVATE KEY-----<br/>MIIJQgIBADANBg... | Similar to SSL_CERT_PEM but should hold the private key of the certificate. |
| PGADMIN_DEFAULT_EMAIL    | user@example.com                                  | The username for logging in.                                 |
| PGADMIN_DEFAULT_PASSWORD | VerySecret!                                       | The password for logging in.                                 |
| PGADMIN_ENABLE_TLS       | TRUE                                              | Should always be set as we have certificates and there seems to be no point on serving plain HTTP. |

See also the [official docs](https://www.pgadmin.org/docs/pgadmin4/latest/container_deployment.html) for additional configuration possibilities.

##### Volumes

| Path in Container | Usage/Remarks                                                |
| ----------------- | ------------------------------------------------------------ |
| /var/lib/pgadmin  | Folder in which pgAdmin stores its files and configuration. Mount these to host file system if settings should be persisted. |


### Changelog

| Tag   | Changes                                          |
| ----- | ------------------------------------------------ |
| 0.1.0 | Initial version. Uses pgAdmin4:5.0 docker image. |
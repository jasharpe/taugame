import base64
import uuid
import os
 
cookie_secret = base64.b64encode(uuid.uuid4().bytes + uuid.uuid4().bytes)

f = open('secrets.py', 'w')
f.write("cookie_secret = '" + cookie_secret + "'\n")
f.write("client_id = ''\n")
f.write("client_secret = ''\n")
f.close()

os.system("""
openssl genrsa -des3 -passout pass:x -out localhost.pass.key 2048 && \
openssl rsa -passin pass:x -in localhost.pass.key -out localhost.key \
&& rm localhost.pass.key && \
openssl req -new -key localhost.key -out localhost.csr
""")

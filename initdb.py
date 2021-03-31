from google.cloud import firestore
import yaml

db = firestore.Client()

is_ref = db.collection('environment').document('imageStatus')
is_content = {'imageStatus' : "Not Created"}
if is_ref.get().exists:
    is_ref.update(is_content)
else:
    is_ref.create(is_content)

anno_ref = db.collection('environment').document('annotators')
anno_content = {'annotators' : []}
if anno_ref.get().exists:
    anno_ref.update(anno_content)
else:
    anno_ref.create(anno_content)

config = yaml.safe_load(open('config.yml'))
users_ref = db.collection('environment').document('authorized-users')
users_content = {'authorizedUsers':config['users']}
if users_ref.get().exists:
    anno_ref.update(users_content)
else:
    users_ref.create(users_content)

manifest_ref = db.collection('environment').document('manifest')
if not manifest_ref.get().exists:
    manifest_ref.create(None)
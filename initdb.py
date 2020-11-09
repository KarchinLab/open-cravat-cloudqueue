from google.cloud import firestore

db = firestore.Client()
is_ref = db.collection(u'environment').document(u'imageStatus')
is_content = {u'imageStatus' : "Not Created"}
if is_ref.get().exists:
    is_ref.update(is_content)
else:
    is_ref.create(is_content)

anno_ref = db.collection(u'environment').document(u'annotators')
anno_content = {u'annotators' : ""}
if anno_ref.get().exists:
    anno_ref.update(anno_content)
else:
    anno_ref.create(anno_content)
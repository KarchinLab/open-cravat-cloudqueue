import oyaml as yaml
import sys
from pathlib import Path

constants_path = 'constants.yml'
env_path = 'env.yml'
app_template = 'app-engine/app-template.yaml'
app_path = 'app-engine/app.yaml'
export_path = 'env.sh'

d = yaml.safe_load(open(constants_path))
conf = yaml.safe_load(open(sys.argv[1]))
project = conf['project']
region = conf['region']
d['GCP_PROJECT'] = project
d['GOOGLE_CLOUD_PROJECT'] = project
d['FUNCTION_REGION'] = region
d['OCQ_BUCKET'] = f'{project}.appspot.com'

sacct_name = d['OCQ_SERVICE_ACCOUNT_NAME']
project = d['GCP_PROJECT']
d['OCQ_SERVICE_ACCOUNT_EMAIL'] = f'{sacct_name}@{project}.iam.gserviceaccount.com'
with open(env_path,'w') as wf:
    wf.write(yaml.dump(d))
with open(app_template,'r') as f:
    app_config = yaml.safe_load(f)
app_config['env_variables'] = d
with open(app_path,'w') as wf:
    wf.write(yaml.dump(app_config))
# Only write this to env.sh
d['GOOGLE_APPLICATION_CREDENTIALS'] = str(Path('app-engine/gcp-key.json').resolve())
with open(export_path,'w') as wf:
    for k,v in d.items():
        wf.write(f'export {k}="{v}"\n')
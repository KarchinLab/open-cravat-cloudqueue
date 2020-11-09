import oyaml as yaml
import sys

constants_path = 'constants.yml'
env_path = 'env.yml'
app_path = 'app-engine/app.yaml'

d = yaml.safe_load(open(constants_path))
conf = yaml.safe_load(open(sys.argv[1]))
d['GCP_PROJECT'] = conf['project']
d['FUNCTION_REGION'] = conf['region']

sacct_name = d['OCQ_SERVICE_ACCOUNT_NAME']
project = d['GCP_PROJECT']
d['OCQ_SERVICE_ACCOUNT_EMAIL'] = f'{sacct_name}@{project}.iam.gserviceaccount.com'
with open(env_path,'w') as wf:
    wf.write(yaml.dump(d))
with open(app_path,'r') as f:
    app_config = yaml.safe_load(f)
app_config['env_variables'] = d
with open(app_path,'w') as wf:
    wf.write(yaml.dump(app_config))
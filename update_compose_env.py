import yaml

file_path = '/data/docker-compose.yml'
with open(file_path, 'r') as f:
    config = yaml.safe_load(f)

if 'napcat' in config['services']:
    env = config['services']['napcat'].get('environment', [])
    # 确保是列表格式
    if isinstance(env, dict):
        env['NAPCAT_WEBUI_TOKEN'] = 'public_demo_key'
    else:
        # 如果是列表，先删除旧的再添加
        env = [item for item in env if 'NAPCAT_WEBUI_TOKEN' not in item]
        env.append('NAPCAT_WEBUI_TOKEN=public_demo_key')
    config['services']['napcat']['environment'] = env

with open(file_path, 'w') as f:
    yaml.dump(config, f, default_flow_style=False, sort_keys=False)

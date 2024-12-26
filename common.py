import boto3
def get_export_value(export_name,cloudformation=None):
    if cloudformation is None:
        cloudformation = boto3.client('cloudformation')    
    response = cloudformation.list_exports()
    exports = response.get('Exports', [])
    
    for export in exports:
        if export['Name'] == export_name:
            return export['Value']
    
    return None
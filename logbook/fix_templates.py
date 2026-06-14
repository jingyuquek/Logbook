import os
import re

# Mapping of old endpoint names to new blueprint-qualified names
endpoint_mapping = {
    # assets blueprint
    'add_vehicle_type': 'assets.add_vehicle_type',
    'remove_vehicle_type': 'assets.remove_vehicle_type',
    'add_type_extinguisher': 'assets.add_type_extinguisher',
    'delete_type_extinguisher': 'assets.delete_type_extinguisher',
    'add_store': 'assets.add_store',
    'edit_store': 'assets.edit_store',
    'remove_store': 'assets.remove_store',
    'move_store': 'assets.move_store',
    'remove_vehicle': 'assets.remove_vehicle',
    'move_vehicle_store': 'assets.move_vehicle_store',
    'add_vehicle': 'assets.add_vehicle',
    'add_extinguisher': 'assets.add_extinguisher',
    'delete_extinguisher': 'assets.delete_extinguisher',
    
    # logbook blueprint
    'logbook': 'logbook.logbook',
    'view_vehicle': 'logbook.view_vehicle',
    'update_pol_level': 'logbook.update_pol_level',
    'perform_gen_run': 'logbook.perform_gen_run',
    'toggle_vor': 'logbook.toggle_vor',
    'delete_logbook_entry': 'logbook.delete_logbook_entry',
    
    # tasks blueprint
    'assign_task': 'tasks.assign_task',
    'company_list': 'tasks.company_list',
    'my_tasks': 'tasks.my_tasks',
    'completed_tasks': 'tasks.completed_tasks',
    'company_tasks': 'tasks.company_tasks',
    'complete_task': 'tasks.complete_task',
    
    # faults blueprint
    'view_faults': 'faults.view_faults',
    'add_fault': 'faults.add_fault',
    
    # transfer blueprint
    'generate_handover_token': 'transfer.generate_handover_token',
    'transit_hub': 'transfer.transit_hub',
    'initiate_handover': 'transfer.initiate_handover',
    'reject_handover': 'transfer.reject_handover',
    'cancel_handover': 'transfer.cancel_handover',
    
    # admin blueprint
    'approve_user': 'admin.approve_user',
    'decline_user': 'admin.decline_user',
    'approve_company_admins': 'admin.approve_company_admins',
    'deny_company_admin': 'admin.deny_company_admin',
    'remove_company_admin': 'admin.remove_company_admin',
    'reset_company_passcode': 'admin.reset_company_passcode',
    'remove_company': 'admin.remove_company',
    'superadmin_dashboard': 'admin.superadmin_dashboard',
    'approve_unit_admin': 'admin.approve_unit_admin',
    'remove_unit_admin': 'admin.remove_unit_admin',
    'unit_admin_dashboard': 'admin.unit_admin_dashboard',
    'reset_unit_passcode': 'admin.reset_unit_passcode',
    'remove_unit': 'admin.remove_unit',
    'deny_unit_admin': 'admin.deny_unit_admin',
    'approve_company_admin': 'admin.approve_company_admin',
}

template_dir = 'app/templates'

for filename in os.listdir(template_dir):
    if filename.endswith('.html'):
        filepath = os.path.join(template_dir, filename)
        with open(filepath, 'r') as f:
            content = f.read()
        
        original_content = content
        
        # Replace url_for calls - need to be careful about order (longer names first)
        for old_endpoint, new_endpoint in sorted(endpoint_mapping.items(), key=lambda x: len(x[0]), reverse=True):
            # Pattern to match url_for('endpoint' or url_for("endpoint"
            pattern = r"url_for\(['\"]" + re.escape(old_endpoint) + r"(['\"])"
            replacement = f"url_for('{new_endpoint}'" + r"\1"
            content = re.sub(pattern, replacement, content)
        
        if content != original_content:
            with open(filepath, 'w') as f:
                f.write(content)
            print(f"Fixed: {filename}")
        else:
            print(f"No changes: {filename}")

print("\nDone!")

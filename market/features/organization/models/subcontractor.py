# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import logging
import requests
import xmlrpc.client
import hashlib

_logger = logging.getLogger(__name__)

class Subcontractor(models.AbstractModel):
    """
    🔗 PURE RPC SUBCONTRACTOR MODEL
    
    Subcontractor model hoàn toàn dựa trên RPC calls đến integration server.
    KHÔNG lưu trữ bất kỳ data nào local, chỉ pure proxy đến remote contractors.
    
    Features:
    - Pure RPC-based, no local storage
    - Direct proxy to integration server contractors
    - Override all view-serving methods
    - Real-time data from remote server
    """
    _name = 'vnfield.subcontractor'
    _description = 'Pure RPC Subcontractor (No Local Storage)'
    _auto = False  # No database table
    
    # ═══════════════════════════════════════════
    # 🏗️ FIELD DEFINITIONS (All Virtual/Computed)
    # ═══════════════════════════════════════════
    
    # All fields are computed from remote data, no local storage
    id = fields.Integer(string='ID')
    name = fields.Char(string='Name')
    description = fields.Text(string='Description') 
    external_id = fields.Char(string='External ID')
    subcontractor_type = fields.Selection([
        ('internal', 'Internal - Nội bộ'),
        ('external', 'External - Bên ngoài'), 
        ('shared', 'Shared - Liên nhà thầu')
    ], string='Subcontractor Type')
    
    representative_id = fields.Many2one('res.users', string='Representative')
    representative_url = fields.Char(string='Representative Server URL')
    
    # Statistics fields
    user_count = fields.Integer(string='User Count')
    team_count = fields.Integer(string='Team Count') 
    project_count = fields.Integer(string='Project Count')
    
    # ═══════════════════════════════════════════
    # 🔌 PURE RPC INTERFACE METHODS
    # ═══════════════════════════════════════════
    
    def _get_remote_contractors(self, domain=None, offset=0, limit=None, order=None):
        """Get contractors from remote server with local field mapping"""
        try:
            # Convert local domain to remote domain
            remote_domain = self._convert_domain_to_remote(domain or [])
            
            # Convert local order to remote order
            remote_order = self._convert_order_to_remote(order or 'name')
            
            # Build search args
            search_args = [remote_domain]
            search_kwargs = {}
            
            if offset:
                search_kwargs['offset'] = offset
            if limit:
                search_kwargs['limit'] = limit
            if remote_order:
                search_kwargs['order'] = remote_order
            
            # Get remote contractor IDs
            remote_ids = self._rpc_call('search', 'vnfield.contractor', search_args, search_kwargs)
            
            if not remote_ids:
                return []
            
            # Read full data for these contractors
            remote_fields = [
                'name', 'description', 'external_id', 'contractor_type',
                'director_id', 'representative_url', 'user_count', 'team_count', 'project_count'
            ]
            
            remote_records = self._rpc_call(
                'read', 
                'vnfield.contractor', 
                [remote_ids], 
                {'fields': remote_fields}
            )
            
            # Convert to local format
            return self._convert_remote_records_to_local(remote_records)
            
        except Exception as e:
            _logger.error(f"Failed to get remote contractors: {str(e)}")
            return []
    
    def _get_remote_contractor_by_id(self, remote_id):
        """Get single contractor from remote server"""
        try:
            remote_records = self._rpc_call(
                'read', 
                'vnfield.contractor', 
                [[remote_id]], 
                {'fields': [
                    'name', 'description', 'external_id', 'contractor_type',
                    'director_id', 'representative_url', 'user_count', 'team_count', 'project_count'
                ]}
            )
            if remote_records:
                converted = self._convert_remote_records_to_local(remote_records)
                return converted[0] if converted else None
            return None
        except Exception as e:
            _logger.error(f"Failed to get remote contractor {remote_id}: {str(e)}")
            return None
    
    # ═══════════════════════════════════════════
    # 🔄 FIELD MAPPING UTILITIES
    # ═══════════════════════════════════════════
    
    def _convert_domain_to_remote(self, domain):
        """Convert local field names in domain to remote field names"""
        if not domain:
            return []
        
        field_mapping = {
            'subcontractor_type': 'contractor_type',
            'representative_id': 'director_id',
        }
        
        converted_domain = []
        for item in domain:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                field, operator, value = item[0], item[1], item[2]
                remote_field = field_mapping.get(field, field)
                converted_domain.append([remote_field, operator, value])
            else:
                converted_domain.append(item)
        
        return converted_domain
    
    def _convert_order_to_remote(self, order):
        """Convert local field names in order to remote field names"""
        if not order:
            return 'name'
        
        field_mapping = {
            'subcontractor_type': 'contractor_type',
            'representative_id': 'director_id',
        }
        
        # Handle simple field name
        if ' ' not in order:
            return field_mapping.get(order, order)
        
        # Handle "field ASC/DESC" format
        parts = order.split(' ')
        field = parts[0]
        direction = parts[1] if len(parts) > 1 else 'ASC'
        remote_field = field_mapping.get(field, field)
        return f"{remote_field} {direction}"
    
    def _convert_remote_records_to_local(self, remote_records):
        """Convert remote contractor records to local subcontractor format"""
        local_records = []
        
        for remote_record in remote_records:
            # Generate virtual ID for AbstractModel
            virtual_id = f"remote_{remote_record['id']}"
            
            local_record = {
                'id': virtual_id,
                'name': remote_record.get('name', 'Unknown'),
                'description': remote_record.get('description', ''),
                'external_id': remote_record.get('external_id', ''),
                'subcontractor_type': remote_record.get('contractor_type', 'external'),
                'representative_url': remote_record.get('representative_url', ''),
                'user_count': remote_record.get('user_count', 0),
                'team_count': remote_record.get('team_count', 0),
                'project_count': remote_record.get('project_count', 0),
            }
            
            # Handle representative_id (Many2one field)
            rep_data = remote_record.get('director_id', False)
            if rep_data and isinstance(rep_data, list) and len(rep_data) > 0:
                local_record['representative_id'] = rep_data[0]  # Take ID from [id, name] tuple
            else:
                local_record['representative_id'] = False
            
            local_records.append(local_record)
        
        return local_records
    
    # ═══════════════════════════════════════════
    # 🎯 PURE RPC VIEW-SERVING METHODS
    # ═══════════════════════════════════════════
    
    @api.model
    def web_search_read(self, domain=None, fields=None, offset=0, limit=None, order=None, specification=None, **kwargs):
        """Override web_search_read for pure RPC implementation"""
        try:
            records = self._get_remote_contractors(domain, offset, limit, order)
            return {
                'records': records,
                'length': len(records)
            }
        except Exception as e:
            _logger.error(f"web_search_read failed: {str(e)}")
            return {'records': [], 'length': 0}
    
    @api.model
    def search(self, domain=None, offset=0, limit=None, order=None, count=False):
        """Override search for pure RPC implementation"""
        try:
            if count:
                # Get count from remote server
                remote_domain = self._convert_domain_to_remote(domain or [])
                remote_count = self._rpc_call('search_count', 'vnfield.contractor', [remote_domain])
                return remote_count
            else:
                # Get records from remote server
                records = self._get_remote_contractors(domain, offset, limit, order)
                # Create recordset with virtual IDs
                virtual_ids = [rec['id'] for rec in records]
                return self.browse(virtual_ids)
        except Exception as e:
            _logger.error(f"search failed: {str(e)}")
            return self.browse([]) if not count else 0
    
    def read(self, fields=None, load='_classic_read'):
        """Override read for pure RPC implementation"""
        try:
            result = []
            for record in self:
                # Extract remote ID from virtual ID
                if isinstance(record.id, str) and record.id.startswith('remote_'):
                    remote_id = int(record.id.replace('remote_', ''))
                    remote_data = self._get_remote_contractor_by_id(remote_id)
                    if remote_data:
                        # Filter fields if specified
                        if fields:
                            filtered_data = {k: v for k, v in remote_data.items() if k in fields}
                            result.append(filtered_data)
                        else:
                            result.append(remote_data)
            return result
        except Exception as e:
            _logger.error(f"read failed: {str(e)}")
            return []
    
    
    def _get_integration_config(self):
        """Lấy cấu hình integration server từ system parameters theo format chuẩn"""
        config_param = self.env['ir.config_parameter'].sudo()
        return {
            'url': config_param.get_param('vnfield.integration_server_url', ''),
            'db': config_param.get_param('vnfield.integration_database', ''),
            'username': config_param.get_param('vnfield.integration_username', ''),
            'api_key': config_param.get_param('vnfield.integration_api_key', ''),
        }
    
    def _get_rpc_connection(self):
        """
        Tạo RPC connection tới integration server theo pattern chuẩn từ contractor_representative_wizard
        Returns: (url, db, uid, api_key, models) tuple or raises exception
        """
        config = self._get_integration_config()
        
        if not config['url']:
            raise UserError(_('Integration server URL not configured. Please configure in system parameters.'))
            
        if not config['db']:
            raise UserError(_('Integration database not configured.'))
            
        if not config['username']:
            raise UserError(_('Integration username not configured.'))
            
        if not config['api_key']:
            raise UserError(_('Integration API key not configured.'))
            
        try:
            # Setup XML-RPC endpoints following Odoo documentation
            server_url = config['url'].rstrip('/')
            common_endpoint = f"{server_url}/xmlrpc/2/common"
            object_endpoint = f"{server_url}/xmlrpc/2/object"
            
            # Step 1: Test connection and get server info
            common = xmlrpc.client.ServerProxy(common_endpoint)
            server_info = common.version()
            _logger.info(f"Connected to Odoo server version: {server_info.get('server_version', 'Unknown')}")
            
            # Step 2: Authenticate using username + API key (replaces password)
            uid = common.authenticate(
                config['db'],
                config['username'],
                config['api_key'],  # API Key used instead of password
                {}
            )
            
            if not uid:
                raise UserError(_('Authentication failed with integration server. Check username and API key.'))
                
            _logger.info(f"Authenticated successfully with UID: {uid}")
            
            models_proxy = xmlrpc.client.ServerProxy(object_endpoint)
            return config['url'], config['db'], uid, config['api_key'], models_proxy
            
        except Exception as e:
            _logger.error(f"RPC connection failed: {str(e)}")
            raise UserError(_('Failed to connect to integration server: %s') % str(e))
    
    def _rpc_call(self, method, model_name='vnfield.contractor', args=None, kwargs=None):
        """
        Execute RPC call to integration server theo chuẩn Odoo 17 với API key authentication
        Args:
            method: string - RPC method name (search, read, create, write, unlink)
            model_name: string - target model name on integration server  
            args: list - positional arguments for the method
            kwargs: dict - keyword arguments for the method
        Returns: RPC result
        """
        try:
            url, db, uid, api_key, models = self._get_rpc_connection()
            
            # Prepare arguments theo format execute_kw chuẩn Odoo
            if args is None:
                args = []
            if kwargs is None:
                kwargs = {}
                
            # Call execute_kw với format: db, uid, api_key, model, method, args, kwargs
            return models.execute_kw(db, uid, api_key, model_name, method, args, kwargs)
            
        except Exception as e:
            _logger.error(f"RPC call failed - method: {method}, model: {model_name}, args: {args}, kwargs: {kwargs}, error: {str(e)}")
            raise UserError(_('RPC call failed: %s') % str(e))
    
    # ═══════════════════════════════════════════
    # � PURE RPC UTILITY METHODS
    # ═══════════════════════════════════════════
    
    @api.model
    def load_views(self, views, options=None):
        """Override load_views to ensure AbstractModel works with views"""
        return super().load_views(views, options)
    
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Override fields_get to ensure field information is available"""
        return super().fields_get(allfields, attributes)
    
    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override _read_group_raw to prevent database queries"""
        return []

    
    # ═══════════════════════════════════════════
    # 🎯 ACTION METHODS
    # ═══════════════════════════════════════════
    
    def action_view_users(self):
        """View users related to this subcontractor via RPC"""
        self.ensure_one()
        try:
            # Extract remote ID from virtual ID
            if isinstance(self.id, str) and self.id.startswith('remote_'):
                remote_id = int(self.id.replace('remote_', ''))
                remote_data = self._get_remote_contractor_by_id(remote_id)
                
                if remote_data:
                    user_count = remote_data.get('user_count', 0)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'info',
                            'title': '👤 Users Information',
                            'message': f'This remote subcontractor has {user_count} users.',
                            'sticky': False,
                        }
                    }
                else:
                    raise UserError(_('Remote contractor data not found'))
            else:
                raise UserError(_('Invalid subcontractor ID'))
                
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '❌ Error',
                    'message': f'Failed to get user information: {str(e)}',
                    'sticky': True,
                }
            }

    def action_view_projects(self):
        """View projects related to this subcontractor via RPC"""
        self.ensure_one()
        try:
            # Extract remote ID from virtual ID
            if isinstance(self.id, str) and self.id.startswith('remote_'):
                remote_id = int(self.id.replace('remote_', ''))
                remote_data = self._get_remote_contractor_by_id(remote_id)
                
                if remote_data:
                    project_count = remote_data.get('project_count', 0)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'info',
                            'title': '🏗️ Projects Information',
                            'message': f'This remote subcontractor has {project_count} projects.',
                            'sticky': False,
                        }
                    }
                else:
                    raise UserError(_('Remote contractor data not found'))
            else:
                raise UserError(_('Invalid subcontractor ID'))
                
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '❌ Error',
                    'message': f'Failed to get project information: {str(e)}',
                    'sticky': True,
                }
            }

    def action_view_teams(self):
        """View teams related to this subcontractor via RPC"""
        self.ensure_one()
        try:
            # Extract remote ID from virtual ID
            if isinstance(self.id, str) and self.id.startswith('remote_'):
                remote_id = int(self.id.replace('remote_', ''))
                remote_data = self._get_remote_contractor_by_id(remote_id)
                
                if remote_data:
                    team_count = remote_data.get('team_count', 0)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'info',
                            'title': '👥 Teams Information',
                            'message': f'This remote subcontractor has {team_count} teams.',
                            'sticky': False,
                        }
                    }
                else:
                    raise UserError(_('Remote contractor data not found'))
            else:
                raise UserError(_('Invalid subcontractor ID'))
                
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '❌ Error',
                    'message': f'Failed to get team information: {str(e)}',
                    'sticky': True,
                }
            }

    def action_register_external(self):
        """Register this subcontractor in external system (placeholder)"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'info',
                'title': '🔧 Registration',
                'message': 'External registration not applicable for remote subcontractors.',
                'sticky': False,
            }
        }

    def action_check_server_status(self):
        """Check server status của subcontractor qua representative_url via RPC"""
        self.ensure_one()
        try:
            # Extract remote ID from virtual ID
            if isinstance(self.id, str) and self.id.startswith('remote_'):
                remote_id = int(self.id.replace('remote_', ''))
                remote_data = self._get_remote_contractor_by_id(remote_id)
                
                if remote_data:
                    url = remote_data.get('representative_url', '')
                    
                    if not url:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'warning',
                                'title': '⚠️ No URL',
                                'message': 'No representative server URL configured for this remote subcontractor.',
                                'sticky': True,
                            }
                        }
                    
                    # Check server status
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        msg = f'Remote server is ONLINE. Status code: 200'
                        msg_type = 'success'
                        title = '✅ Server Online'
                    else:
                        msg = f'Remote server responded with status code: {response.status_code}'
                        msg_type = 'warning'
                        title = '⚠️ Server Response'
                else:
                    raise UserError(_('Remote contractor data not found'))
            else:
                raise UserError(_('Invalid subcontractor ID'))
                
        except requests.RequestException as e:
            msg = f'Failed to connect to remote server: {str(e)}'
            msg_type = 'danger'
            title = '❌ Connection Failed'
        except Exception as e:
            msg = f'Error checking remote subcontractor: {str(e)}'
            msg_type = 'danger'
            title = '❌ Error'
            
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': msg_type,
                'title': title,
                'message': msg,
                'sticky': False,
            }
        }

    def action_open_representative_interface(self):
        """Open representative interface trong browser via RPC"""
        self.ensure_one()
        try:
            # Extract remote ID from virtual ID
            if isinstance(self.id, str) and self.id.startswith('remote_'):
                remote_id = int(self.id.replace('remote_', ''))
                remote_data = self._get_remote_contractor_by_id(remote_id)
                
                if remote_data:
                    url = remote_data.get('representative_url', '')
                    
                    if not url:
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'type': 'warning',
                                'title': '⚠️ No URL',
                                'message': 'No representative server URL configured for this remote subcontractor.',
                                'sticky': True,
                            }
                        }
                        
                    return {
                        'type': 'ir.actions.act_url',
                        'url': url,
                        'target': 'new',
                    }
                else:
                    raise UserError(_('Remote contractor data not found'))
            else:
                raise UserError(_('Invalid subcontractor ID'))
                
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '❌ Error',
                    'message': f'Error opening representative interface: {str(e)}',
                    'sticky': True,
                }
            }
    
    # ═══════════════════════════════════════════
    # 🔧 UTILITY METHODS
    # ═══════════════════════════════════════════
    
    @api.model
    def load_views(self, views, options=None):
        """Override load_views to ensure AbstractModel works with views"""
        return super().load_views(views, options)
    
    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Override fields_get to ensure field information is available"""
        return super().fields_get(allfields, attributes)
    
    @api.model
    def _read_group_raw(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Override _read_group_raw to prevent database queries"""
        return []
    
    @api.model 
    def _search(self, domain=None, offset=0, limit=None, order=None, access_rights_uid=None):
        """Override _search for pure AbstractModel - no database queries"""
        # AbstractModel should not perform database searches
        return []
    
    def _read_format(self, fnames, load='_classic_read'):
        """Override _read_format to use our custom read implementation"""
        return self.read(fnames, load)
    
    def _read(self, fields=None, load='_classic_read'):
        """Override _read to use our custom read implementation"""
        return self.read(fields, load)
    
    @api.model
    def test_integration_connection(self):
        """Test method để kiểm tra kết nối với integration server theo pattern chuẩn"""
        try:
            config = self._get_integration_config()
            url, db, uid, api_key, models = self._get_rpc_connection()
            
            # Test search contractors với proper format và limit
            contractor_ids = self._rpc_call('search', 'vnfield.contractor', [[]], {'limit': 5})
            contractor_count = len(contractor_ids)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'title': '✅ Integration Connection Test Success',
                    'message': f'Connected to {config["url"]} with username/API key successfully. Found {contractor_count} contractors.',
                    'sticky': False,
                }
            }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'danger',
                    'title': '❌ Integration Connection Test Failed',
                    'message': f'Connection failed: {str(e)}',
                    'sticky': True,
                }
            }

    # ─────────────────────────────────────────────
    # ▶ LEGACY METHODS (Removed duplicates)
    # ─────────────────────────────────────────────

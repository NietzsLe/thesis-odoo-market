# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MarketCapacityProfile(models.Model):
    """
    🏗️ MODEL: Hồ sơ năng lực của contractor
    - Mô tả khả năng, kinh nghiệm của contractor
    - Được sử dụng để match với requirement
    """
    _name = 'vnfield.market.capacity.profile'
    _description = 'Capacity Profile - Hồ sơ năng lực'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'title'

    # ═══════════════════════════════════════════
    # ▶ BASIC FIELDS
    # ═══════════════════════════════════════════
    
    title = fields.Char(
        string='Tiêu đề hồ sơ',
        required=True,
        help='Tiêu đề mô tả ngắn gọn về năng lực'
    )
    
    description = fields.Html(
        string='Mô tả chi tiết',
        help='Mô tả chi tiết về năng lực và kinh nghiệm'
    )
    
    contractor_id = fields.Many2one(
        'vnfield.contractor',
        string='Nhà thầu',
        required=True,
        default=lambda self: self._get_current_contractor(),
        help='Nhà thầu sở hữu hồ sơ năng lực này'
    )
    
    state = fields.Selection([
        ('waiting_match', 'Waiting Match'),
        ('matched', 'Matched'),
        ('inactive', 'Inactive')
    ], string='Trạng thái', default='waiting_match', tracking=True)
    
    # ═══════════════════════════════════════════
    # ▶ CAPACITY DETAILS
    # ═══════════════════════════════════════════
    
    work_category = fields.Selection([
        ('construction', 'Thi công xây dựng'),
        ('design', 'Thiết kế'),
        ('consulting', 'Tư vấn'),
        ('supervision', 'Giám sát'),
        ('survey', 'Khảo sát'),
        ('testing', 'Thí nghiệm'),
        ('other', 'Khác')
    ], string='Lĩnh vực chuyên môn', required=True)
    
    experience_years = fields.Integer(
        string='Kinh nghiệm (năm)',
        help='Số năm kinh nghiệm trong lĩnh vực'
    )
    
    team_size = fields.Integer(
        string='Quy mô đội ngũ',
        help='Số lượng nhân viên có thể tham gia dự án'
    )
    
    # ═══════════════════════════════════════════
    # ▶ BUSINESS CAPACITY
    # ═══════════════════════════════════════════
    
    budget_capacity_min = fields.Monetary(
        string='Ngân sách tối thiểu',
        currency_field='currency_id',
        help='Ngân sách dự án tối thiểu có thể đảm nhận'
    )
    
    budget_capacity_max = fields.Monetary(
        string='Ngân sách tối đa',
        currency_field='currency_id',
        help='Ngân sách dự án tối đa có thể đảm nhận'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Tiền tệ',
        default=lambda self: self.env.company.currency_id
    )
    
    # ═══════════════════════════════════════════
    # ▶ AVAILABILITY
    # ═══════════════════════════════════════════
    
    available_from = fields.Date(
        string='Có thể bắt đầu từ',
        help='Ngày sớm nhất có thể bắt đầu dự án mới'
    )
    
    max_project_duration = fields.Integer(
        string='Thời gian dự án tối đa (tháng)',
        help='Thời gian dài nhất có thể cam kết cho một dự án'
    )
    
    current_workload = fields.Selection([
        ('low', 'Thấp (0-30%)'),
        ('medium', 'Trung bình (30-70%)'),
        ('high', 'Cao (70-90%)'),
        ('full', 'Đầy tải (90-100%)')
    ], string='Mức độ bận rộn hiện tại', default='low')
    
    # ═══════════════════════════════════════════
    # ▶ QUALIFICATIONS
    # ═══════════════════════════════════════════
    
    certifications = fields.Text(
        string='Chứng chỉ & Bằng cấp',
        help='Các chứng chỉ, bằng cấp chuyên môn'
    )
    
    completed_projects = fields.Integer(
        string='Dự án đã hoàn thành',
        help='Số lượng dự án tương tự đã hoàn thành'
    )
    
    reference_projects = fields.Text(
        string='Dự án tham chiếu',
        help='Danh sách các dự án tiêu biểu đã thực hiện'
    )
    
    # ═══════════════════════════════════════════
    # ▶ LOCATION & PREFERENCES
    # ═══════════════════════════════════════════
    
    service_locations = fields.Text(
        string='Khu vực phục vụ',
        help='Các khu vực có thể cung cấp dịch vụ'
    )
    
    preferred_project_types = fields.Text(
        string='Loại dự án ưu tiên',
        help='Các loại dự án mong muốn tham gia'
    )
    
    # ═══════════════════════════════════════════
    # ▶ MATCHING
    # ═══════════════════════════════════════════
    
    requirement_ids = fields.Many2many(
        'vnfield.market.requirement',
        'requirement_capacity_match_rel',
        'capacity_id',
        'requirement_id',
        string='Yêu cầu phù hợp',
        help='Các yêu cầu mà hồ sơ này phù hợp'
    )
    
    # ═══════════════════════════════════════════
    # ▶ COMPUTED FIELDS
    # ═══════════════════════════════════════════
    
    match_count = fields.Integer(
        string='Số lượng match',
        compute='_compute_match_count'
    )
    
    # ═══════════════════════════════════════════
    # ▶ COMPUTE METHODS
    # ═══════════════════════════════════════════
    
    def _compute_match_count(self):
        for record in self:
            record.match_count = len(record.requirement_ids)
    
    # ═══════════════════════════════════════════
    # ▶ HELPER METHODS
    # ═══════════════════════════════════════════
    
    def _get_current_contractor(self):
        """Lấy contractor của user hiện tại"""
        if self.env.user.contractor_id:
            return self.env.user.contractor_id.id
        return False
    
    # ═══════════════════════════════════════════
    # ▶ VALIDATION
    # ═══════════════════════════════════════════
    
    @api.constrains('budget_capacity_min', 'budget_capacity_max')
    def _check_budget_capacity(self):
        for record in self:
            if record.budget_capacity_min and record.budget_capacity_max:
                if record.budget_capacity_min > record.budget_capacity_max:
                    raise ValidationError(_("Ngân sách tối đa phải lớn hơn ngân sách tối thiểu"))
    
    # ═══════════════════════════════════════════
    # ▶ ACTIONS
    # ═══════════════════════════════════════════
    
    def action_activate(self):
        """Kích hoạt hồ sơ năng lực"""
        self.state = 'waiting_match'
        self.action_find_matches()
    
    def action_find_matches(self):
        """Tìm kiếm requirement phù hợp"""
        self.ensure_one()
        
        # Tìm requirement phù hợp dựa trên các tiêu chí
        domain = [
            ('state', 'in', ['waiting_match', 'matched']),
            ('work_category', '=', self.work_category),
            ('contractor_id', '!=', self.contractor_id.id)  # Không match với chính mình
        ]
        
        # Lọc theo kinh nghiệm
        if self.experience_years:
            domain.append(('required_experience_years', '<=', self.experience_years))
        
        # Lọc theo ngân sách
        if self.budget_capacity_min:
            domain.append(('budget_min', '>=', self.budget_capacity_min))
        if self.budget_capacity_max:
            domain.append(('budget_max', '<=', self.budget_capacity_max))
        
        matches = self.env['vnfield.market.requirement'].search(domain)
        self.requirement_ids = matches
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Tìm thấy {len(matches)} yêu cầu phù hợp!',
                'type': 'success',
            }
        }

    def _auto_match_requirement(self):
        """🎯 Tự động matching với requirement khi tạo mới capacity profile"""
        self.ensure_one()
        
        # Tìm requirement đang chờ match và phù hợp
        domain = [
            ('state', '=', 'waiting_match'),
            ('work_category', '=', self.work_category),
            ('contractor_id', '!=', self.contractor_id.id)  # Không match với chính mình
        ]
        
        # Lọc theo kinh nghiệm nếu có
        if self.experience_years:
            domain.append(('required_experience_years', '<=', self.experience_years))
        
        # Tìm requirement được tạo sớm nhất
        requirement = self.env['vnfield.market.requirement'].search(domain, order='create_date asc', limit=1)
        
        if requirement:
            # Thực hiện matching
            self.requirement_ids = [(6, 0, [requirement.id])]
            requirement.capacity_profile_ids = [(6, 0, [self.id])]
            
            # Cập nhật trạng thái
            self.state = 'matched'
            requirement.state = 'matched'
            
            # Gửi pubsub messages
            self._send_match_messages(requirement)
            
            return requirement
        
        return False

    def _send_match_messages(self, requirement):
        """📨 Gửi pubsub messages khi có matching"""
        try:
            config_param = self.env['ir.config_parameter'].sudo()
            topic = config_param.get_param('vnfield.kafka.topic', 'vnfield')
            
            # Message cho capacity profile owner
            capacity_message = {
                'destination': self.contractor_id.name,  # Tên contractor sở hữu capacity profile
                'action': 'match_capacity_profile',
                'vals': {
                    'requirement_id': requirement.id,
                    'capacity_profile_id': self.id,
                    'task_id': requirement.task_id if requirement.task_id else None,  # Task ID từ requirement
                    'requirement_contractor_id': requirement.contractor_id.id,  # ID contractor sở hữu requirement
                    'capacity_contractor_id': self.contractor_id.id,  # ID contractor sở hữu capacity profile
                    'requirement_contractor_name': requirement.contractor_id.name,  # Tên contractor sở hữu requirement
                    'capacity_contractor_name': self.contractor_id.name,  # Tên contractor sở hữu capacity profile
                    'requirement_title': requirement.title,  # Title của requirement
                    'capacity_profile_title': self.title,  # Title của capacity profile
                },
                'extra': {
                    'timestamp': fields.Datetime.now().replace(tzinfo=None).replace(microsecond=0).isoformat() + '+07:00',
                    'priority': 'high'
                }
            }
            
            # Message cho requirement owner
            requirement_message = {
                'destination': requirement.contractor_id.name,  # Tên contractor sở hữu requirement
                'action': 'match_requirement',
                'vals': {
                    'requirement_id': requirement.id,
                    'capacity_profile_id': self.id,
                    'task_id': requirement.task_id if requirement.task_id else None,  # Task ID từ requirement
                    'requirement_contractor_id': requirement.contractor_id.id,  # ID contractor sở hữu requirement
                    'capacity_contractor_id': self.contractor_id.id,  # ID contractor sở hữu capacity profile
                    'requirement_contractor_name': requirement.contractor_id.name,  # Tên contractor sở hữu requirement
                    'capacity_contractor_name': self.contractor_id.name,  # Tên contractor sở hữu capacity profile
                    'requirement_title': requirement.title,  # Title của requirement
                    'capacity_profile_title': self.title,  # Title của capacity profile
                },
                'extra': {
                    'timestamp': fields.Datetime.now().replace(tzinfo=None).replace(microsecond=0).isoformat() + '+07:00',
                    'priority': 'high'
                }
            }
            
            # Gửi messages
            pubsub_service = self.env['vnfield.pubsub.service'].create({})
            pubsub_service.produce_message(topic, capacity_message)
            pubsub_service.produce_message(topic, requirement_message)
            
        except Exception as e:
            # Log error nhưng không fail transaction
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"Error sending match messages: {e}")

    @api.model
    def create(self, vals):
        """Override create để thực hiện auto matching"""
        record = super().create(vals)
        
        # Thực hiện auto matching nếu state là waiting_match
        if record.state == 'waiting_match':
            record._auto_match_requirement()
        
        return record
    
    def action_view_matches(self):
        """Xem danh sách requirement phù hợp"""
        return {
            'name': _('Yêu cầu phù hợp'),
            'type': 'ir.actions.act_window',
            'res_model': 'vnfield.market.requirement',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.requirement_ids.ids)],
            'context': {'default_capacity_profile_id': self.id}
        }

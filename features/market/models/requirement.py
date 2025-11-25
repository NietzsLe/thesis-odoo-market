# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class MarketRequirement(models.Model):
    """
    🏗️ MODEL: Yêu cầu công việc thuê ngoài trong xây dựng
    - Được tạo bởi contractor cần thuê ngoài công việc
    - Có thể được match với capacity profile của các contractor khác
    """
    _name = 'vnfield.market.requirement'
    _description = 'Market Requirement - Yêu cầu thuê ngoài'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'
    _rec_name = 'title'

    # ═══════════════════════════════════════════
    # ▶ BASIC FIELDS
    # ═══════════════════════════════════════════
    
    title = fields.Char(
        string='Tiêu đề yêu cầu',
        required=True,
        help='Tiêu đề mô tả ngắn gọn yêu cầu công việc'
    )
    
    task_id = fields.Integer(
        string='Task ID',
        help='Mã số task/nhiệm vụ (optional)'
    )
    
    description = fields.Html(
        string='Mô tả chi tiết',
        help='Mô tả chi tiết về yêu cầu công việc'
    )
    
    contractor_id = fields.Many2one(
        'vnfield.contractor',
        string='Nhà thầu yêu cầu',
        required=True,
        default=lambda self: self._get_current_contractor(),
        help='Nhà thầu tạo yêu cầu này'
    )
    
    state = fields.Selection([
        ('waiting_match', 'Waiting Match'),
        ('matched', 'Matched'),
        ('inactive', 'Inactive')
    ], string='Trạng thái', default='waiting_match', tracking=True)
    
    # ═══════════════════════════════════════════
    # ▶ WORK DETAILS
    # ═══════════════════════════════════════════
    
    work_category = fields.Selection([
        ('construction', 'Thi công xây dựng'),
        ('design', 'Thiết kế'),
        ('consulting', 'Tư vấn'),
        ('supervision', 'Giám sát'),
        ('survey', 'Khảo sát'),
        ('testing', 'Thí nghiệm'),
        ('other', 'Khác')
    ], string='Loại công việc', required=True)
    
    location = fields.Char(
        string='Địa điểm thực hiện',
        help='Địa điểm thực hiện công việc'
    )
    
    budget_min = fields.Monetary(
        string='Ngân sách tối thiểu',
        currency_field='currency_id'
    )
    
    budget_max = fields.Monetary(
        string='Ngân sách tối đa',
        currency_field='currency_id'
    )
    
    currency_id = fields.Many2one(
        'res.currency',
        string='Tiền tệ',
        default=lambda self: self.env.company.currency_id
    )
    
    start_date = fields.Date(
        string='Ngày bắt đầu dự kiến',
        help='Ngày dự kiến bắt đầu thực hiện'
    )
    
    end_date = fields.Date(
        string='Ngày hoàn thành dự kiến',
        help='Ngày dự kiến hoàn thành'
    )
    
    duration_months = fields.Integer(
        string='Thời gian thực hiện (tháng)',
        compute='_compute_duration_months',
        store=True
    )
    
    # ═══════════════════════════════════════════
    # ▶ REQUIREMENTS & QUALIFICATIONS
    # ═══════════════════════════════════════════
    
    required_experience_years = fields.Integer(
        string='Kinh nghiệm yêu cầu (năm)',
        help='Số năm kinh nghiệm tối thiểu'
    )
    
    required_certifications = fields.Text(
        string='Chứng chỉ yêu cầu',
        help='Các chứng chỉ, bằng cấp cần thiết'
    )
    
    team_size_min = fields.Integer(
        string='Quy mô nhóm tối thiểu'
    )
    
    team_size_max = fields.Integer(
        string='Quy mô nhóm tối đa'
    )
    
    # ═══════════════════════════════════════════
    # ▶ MATCHING & BIDDING
    # ═══════════════════════════════════════════
    
    capacity_profile_ids = fields.Many2many(
        'vnfield.market.capacity.profile',
        'requirement_capacity_match_rel',
        'requirement_id',
        'capacity_id',
        string='Hồ sơ năng lực phù hợp',
        help='Các hồ sơ năng lực được hệ thống gợi ý phù hợp'
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
    
    @api.depends('start_date', 'end_date')
    def _compute_duration_months(self):
        for record in self:
            if record.start_date and record.end_date:
                delta = record.end_date - record.start_date
                record.duration_months = max(1, delta.days // 30)
            else:
                record.duration_months = 0
    
    def _compute_match_count(self):
        for record in self:
            record.match_count = len(record.capacity_profile_ids)
    
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
    
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date:
                if record.start_date >= record.end_date:
                    raise ValidationError(_("Ngày kết thúc phải sau ngày bắt đầu"))
    
    @api.constrains('budget_min', 'budget_max')
    def _check_budget(self):
        for record in self:
            if record.budget_min and record.budget_max:
                if record.budget_min > record.budget_max:
                    raise ValidationError(_("Ngân sách tối đa phải lớn hơn ngân sách tối thiểu"))
    
    @api.constrains('team_size_min', 'team_size_max')
    def _check_team_size(self):
        for record in self:
            if record.team_size_min and record.team_size_max:
                if record.team_size_min > record.team_size_max:
                    raise ValidationError(_("Quy mô nhóm tối đa phải lớn hơn quy mô tối thiểu"))
    
    # ═══════════════════════════════════════════
    # ▶ ACTIONS
    # ═══════════════════════════════════════════
    
    def action_publish(self):
        """Đăng yêu cầu để tìm đối tác"""
        self.state = 'waiting_match'
        self.action_find_matches()
    
    def action_find_matches(self):
        """Tìm kiếm capacity profile phù hợp"""
        self.ensure_one()
        
        # Tìm capacity profile phù hợp dựa trên các tiêu chí
        domain = [
            ('state', '=', 'waiting_match'),
            ('work_category', '=', self.work_category),
            ('contractor_id', '!=', self.contractor_id.id)  # Không match với chính mình
        ]
        
        # Lọc theo kinh nghiệm
        if self.required_experience_years:
            domain.append(('experience_years', '>=', self.required_experience_years))
        
        matches = self.env['vnfield.market.capacity.profile'].search(domain)
        self.capacity_profile_ids = matches
        
        if matches:
            self.state = 'matched'
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': f'Tìm thấy {len(matches)} hồ sơ năng lực phù hợp!',
                'type': 'success',
            }
        }

    def _auto_match_capacity_profile(self):
        """🎯 Tự động matching với capacity profile khi tạo mới requirement"""
        self.ensure_one()
        
        # Tìm capacity profile đang chờ match và phù hợp
        domain = [
            ('state', '=', 'waiting_match'),
            ('work_category', '=', self.work_category),
            ('contractor_id', '!=', self.contractor_id.id)  # Không match với chính mình
        ]
        
        # Lọc theo kinh nghiệm nếu có
        if self.required_experience_years:
            domain.append(('experience_years', '>=', self.required_experience_years))
        
        # Tìm capacity profile được tạo sớm nhất
        capacity_profile = self.env['vnfield.market.capacity.profile'].search(domain, order='create_date asc', limit=1)
        
        if capacity_profile:
            # Thực hiện matching
            self.capacity_profile_ids = [(6, 0, [capacity_profile.id])]
            capacity_profile.requirement_ids = [(6, 0, [self.id])]
            
            # Cập nhật trạng thái
            self.state = 'matched'
            capacity_profile.state = 'matched'
            
            # Gửi pubsub messages
            self._send_match_messages(capacity_profile)
            
            return capacity_profile
        
        return False

    def _send_match_messages(self, capacity_profile):
        """📨 Gửi pubsub messages khi có matching"""
        try:
            config_param = self.env['ir.config_parameter'].sudo()
            topic = config_param.get_param('vnfield.kafka.topic', 'vnfield')
            
            # Message cho requirement owner
            requirement_message = {
                'destination': self.contractor_id.name,  # Tên contractor sở hữu requirement
                'action': 'match_requirement',
                'vals': {
                    'requirement_id': self.id,
                    'capacity_profile_id': capacity_profile.id,
                    'task_id': self.task_id if self.task_id else None,  # Task ID từ requirement
                    'requirement_contractor_id': self.contractor_id.id,  # ID contractor sở hữu requirement
                    'capacity_contractor_id': capacity_profile.contractor_id.id,  # ID contractor sở hữu capacity profile
                    'requirement_contractor_name': self.contractor_id.name,  # Tên contractor sở hữu requirement
                    'capacity_contractor_name': capacity_profile.contractor_id.name,  # Tên contractor sở hữu capacity profile
                    'requirement_title': self.title,  # Title của requirement
                    'capacity_profile_title': capacity_profile.title,  # Title của capacity profile
                },
                'extra': {
                    'timestamp': fields.Datetime.now().replace(tzinfo=None).replace(microsecond=0).isoformat() + '+07:00',
                    'priority': 'high'
                }
            }
            
            # Message cho capacity profile owner
            capacity_message = {
                'destination': capacity_profile.contractor_id.name,  # Tên contractor sở hữu capacity profile
                'action': 'match_capacity_profile',
                'vals': {
                    'requirement_id': self.id,
                    'capacity_profile_id': capacity_profile.id,
                    'task_id': self.task_id if self.task_id else None,  # Task ID từ requirement
                    'requirement_contractor_id': self.contractor_id.id,  # ID contractor sở hữu requirement
                    'capacity_contractor_id': capacity_profile.contractor_id.id,  # ID contractor sở hữu capacity profile
                    'requirement_contractor_name': self.contractor_id.name,  # Tên contractor sở hữu requirement
                    'capacity_contractor_name': capacity_profile.contractor_id.name,  # Tên contractor sở hữu capacity profile
                    'requirement_title': self.title,  # Title của requirement
                    'capacity_profile_title': capacity_profile.title,  # Title của capacity profile
                },
                'extra': {
                    'timestamp': fields.Datetime.now().replace(tzinfo=None).replace(microsecond=0).isoformat() + '+07:00',
                    'priority': 'high'
                }
            }
            
            # Gửi messages
            pubsub_service = self.env['vnfield.pubsub.service'].create({})
            pubsub_service.produce_message(topic, requirement_message)
            pubsub_service.produce_message(topic, capacity_message)
            
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
            record._auto_match_capacity_profile()
        
        return record
    
    def action_view_matches(self):
        """Xem danh sách capacity profile phù hợp"""
        return {
            'name': _('Hồ sơ năng lực phù hợp'),
            'type': 'ir.actions.act_window',
            'res_model': 'vnfield.market.capacity.profile',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.capacity_profile_ids.ids)],
            'context': {'default_requirement_id': self.id}
        }
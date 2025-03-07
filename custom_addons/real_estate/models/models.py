
from odoo import models,fields,api
from datetime import timedelta
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_compare, float_is_zero


class Estate_Property(models.Model):
    _name = "estate.property"
    _description = "This is Real Estate Profile."
    _order = "id desc"

    name=fields.Char(required=True,string="Title" )

    description=fields.Text()

    postcode=fields.Char()

    date_availability=fields.Date(string="Available From",default=lambda self: fields.Date.today() + timedelta(days=90), copy=False)

    expected_price=fields.Float(required=True)

    selling_price=fields.Float(readonly=True,copy=False)

    bedrooms=fields.Integer(default="2")

    living_area=fields.Integer(string="Living Area (sqm)")

    facades=fields.Integer()

    garage=fields.Boolean()

    garden=fields.Boolean()

    garden_area=fields.Integer(string="Garden Area (sqm)")

    garden_orientation=fields.Selection(
        [("north","North"),
         ("south","South"),
         ("east","East"),
         ("west","West")]
    )

    active=fields.Boolean(default=True)

    status=fields.Selection([
        ("new","New"),
        ("offer_received","Offer Received"),
        ("offer_accepted","Offer Accepted"),
        ("sold","Sold"),
        ("cancelled","Cancelled")
    ], required=True,copy=False,default="new")

    property_type_id=fields.Many2one("estate.property.type",string="Property Type",ondelete="set null",domain=[],index=True,)

    buyer_id=fields.Many2one("res.partner",string="Buyer",copy=False)

    seller_id=fields.Many2one("res.users",string="Salesman",default=lambda self: self.env.user)

    tag_ids=fields.Many2many("estate.property.tag",string="Name")

    offer_ids=fields.One2many("estate.property.offer", "property_id", string="Offers")

    total_area=fields.Float(compute="_compute_total")
    
    best_price = fields.Float(string="Best Offer", compute="_compute_best_price", store=True)



    @api.onchange("living_area","garden_area")
    def _compute_total(self):
        for record in self:
            record.total_area=record.living_area + record.garden_area
        


    @api.depends("offer_ids.price")
    def _compute_best_price(self):
        for property in self:
            property.best_price = max(property.offer_ids.mapped("price"), default=0)


    # Sets default values when garden is True and clears them when False.
    @api.onchange("garden")
    def _onchange_garden(self):
        if self.garden:
            self.garden_area = 10
            self.garden_orientation = "north"
        else:
            self.garden_area = 0
            self.garden_orientation = False

    hide_sold = fields.Boolean(compute="_compute_button_visibility")
    hide_cancel = fields.Boolean(compute="_compute_button_visibility")

    @api.depends("status")
    def _compute_button_visibility(self):
        for record in self:
            record.hide_sold = record.status != "offer_accepted"
            record.hide_cancel = record.status in ["sold", "cancelled"]

    def action_sold(self):
        for record in self:
            if record.status == "cancelled":
                raise UserError("Cancelled property cannot be sold!")
            if record.status != "offer_accepted":
                raise UserError("You can only sell a property if an offer has been accepted.")
            record.status = "sold"

    def action_cancel(self):
        for record in self:
            if record.status == "sold":
                raise UserError("Sold property cannot be cancelled!")
            record.status = "cancelled"

    _sql_constraints = [
        ("check_expected_price", "CHECK(expected_price > 0)", "Expected price must be strictly positive."),
        ("check_selling_price", "CHECK(selling_price >= 0)", "Selling price must be positive.")
    ]

    @api.constrains("expected_price", "selling_price")
    def _check_price_values(self):
        for record in self:
            if record.expected_price <= 0:
                raise ValidationError("Expected price must be strictly positive.")
            if record.selling_price < 0:
                raise ValidationError("Selling price must be positive.")
         # Ensure selling price is at least 90% of expected price (unless it's zero)
            min_acceptable_price = record.expected_price * 0.9
            if not float_is_zero(record.selling_price, precision_digits=2) and \
               float_compare(record.selling_price, min_acceptable_price, precision_digits=2) < 0:
                raise ValidationError("Selling price cannot be lower than 90% of the expected price.")
            
    @api.ondelete(at_uninstall=False)
    def _prevent_deletion(self):
        for record in self:
            if record.status not in ("new", "cancelled"):
                raise UserError("You can only delete properties that are 'New' or 'Cancelled'.")


#-----------------------Property type model -------------------

class Estate_Property_Type(models.Model):
    _name = "estate.property.type"
    _description = "This is Real Estate property type profile."
    _order = "sequence,name asc"

    name=fields.Char(required=True,string="Name" )
    sequence = fields.Integer(string="Sequence", default=1)

    property_ids=fields.One2many("estate.property","property_type_id")

    offer_ids = fields.One2many("estate.property.offer", "property_type_id", string="Offers")

    offer_count = fields.Integer(
        string=" Offer Count",
        compute="_compute_offer_count"
    )
    def _compute_offer_count(self):
        for record in self:
            record.offer_count = len(record.offer_ids)

    _sql_constraints = [
        ("unique_type_name", "UNIQUE(name)", "Property type name must be unique.")
    ]

    @api.constrains("name")
    def _check_unique_name(self):
        for record in self:
            existing = self.search([
                ("id", "!=", record.id),
                ("name", "=ilike", record.name)  # Case-insensitive check
            ])
            if existing:
                raise ValidationError("Property type name must be unique (case insensitive).")
            
    def action_view_offers(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Offers",
            "res_model": "estate.property.offer",
            "view_mode": "list,form",
            "domain": [("property_type_id", "=", self.id)],
            "context": {"default_property_type_id": self.id},
        }



#-----------------------Property tag model -------------------

class Estate_Property_Tag(models.Model):
    _name = "estate.property.tag"
    _description = "This is Real Estate property tag profile."
    _order = "name asc"

    name=fields.Char(required=True,string="Name")
    color = fields.Integer(string="Color")

    _sql_constraints = [
        ("unique_tag_name", "UNIQUE(name)", "Property Tag name must be unique.")
    ]
    @api.constrains("name")
    def _check_unique_name(self):
        for record in self:
            existing = self.search([
                ("id", "!=", record.id),
                ("name", "=ilike", record.name)  # Case-insensitive check
            ])
            if existing:
                raise ValidationError("Property tag name must be unique (case insensitive).")
            

#-----------------------Property offer model -------------------

class Estate_Property_Offer(models.Model):
    _name = "estate.property.offer"
    _description = "This is Real Estate property offer profile."
    _order = "price desc"

    price=fields.Float()

    status=fields.Selection([("accepted","Accepted"),
                             ("refused","Refused")],copy=False)

    partner_id=fields.Many2one("res.partner",required=1,string="Partner")

    property_id=fields.Many2one("estate.property",required=1,ondelete="cascade")

    validity = fields.Integer(string="Validity (days)", default=7)

    property_type_id = fields.Many2one(
        "estate.property.type",
        string="Property Type",
        related="property_id.property_type_id",
        store=True
    )

    date_deadline = fields.Date(
        string="Deadline",
        compute="_compute_date_deadline",
        inverse="_inverse_date_deadline",
        store=True
    )

    _sql_constraints = [
        ("check_offer_price", "CHECK(price > 0)", "Offer price must be strictly positive.")
    ]

        #  Compute the deadline as create_date + validity days 
    @api.depends("create_date", "validity")
    def _compute_date_deadline(self):
        for offer in self:
            create_date = offer.create_date.date() if offer.create_date else fields.Date.today()
            offer.date_deadline = create_date + timedelta(days=offer.validity)

        #  Allow users to modify either the validity or the deadline
    def _inverse_date_deadline(self):
        for offer in self:
            create_date = offer.create_date.date() if offer.create_date else fields.Date.today()
            offer.validity = (offer.date_deadline - create_date).days

    hide_accept = fields.Boolean(compute="_compute_button_visibility")
    hide_refuse = fields.Boolean(compute="_compute_button_visibility")

    @api.depends("status")
    def _compute_button_visibility(self):
        for record in self:
            record.hide_accept = record.status == "accepted"
            record.hide_refuse = record.status == "refused"

    def action_accept(self):
        for record in self:
            if record.property_id.offer_ids.filtered(lambda o: o.status == "accepted"):
                raise UserError("Only one offer can be accepted for a property!")
            record.status = "accepted"
            record.property_id.selling_price = record.price
            record.property_id.buyer_id = record.partner_id
            record.property_id.status = "offer_accepted" 

    def action_refuse(self):
        for record in self:
            record.status = "refused"

    
    @api.model
    def create(self, vals):
    # Get the property record
        property_record = self.env["estate.property"].browse(vals["property_id"])

    # Ensure property_record has offers before trying to get the best price
        if property_record.offer_ids:
            best_price = max(property_record.offer_ids.mapped("price"))
        else:
            best_price = 0  # Default value if no offers exist

    # Check if the new offer is lower than an existing best offer
        if vals["price"] < best_price:
            raise UserError("New offers must be higher than {:.2f}.".format(best_price))

    # Save the offer first
        new_offer = super(Estate_Property_Offer, self).create(vals)

    # Check if this new offer is the best offer
        if new_offer.price >= max(property_record.offer_ids.mapped("price"), default=0):
            property_record.status = "offer_received"

        return new_offer

# ---------------------------Res user model ----------------------------
class Res_Users(models.Model):
    _inherit = "res.users"

    property_ids = fields.One2many(
        "estate.property",  # Related model
        "seller_id",  # Inverse field in estate.property
        string="Properties"
    )
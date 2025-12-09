# -*- coding: utf-8 -*-
"""
Electricity Billing Calculator with Tiered Pricing
Vietnamese electricity pricing system
"""

from config import ELECTRICITY_TIERS, VAT_RATE
import copy


class ElectricityCalculator:
    """
    Calculates electricity bill using Vietnamese tiered pricing
    Bậc thang giá điện sinh hoạt Việt Nam
    """
    
    def __init__(self):
        self.tiers = copy.deepcopy(ELECTRICITY_TIERS)
        self.vat_rate = VAT_RATE
    
    def update_tier_prices(self, prices: list, vat: float = None):
        """
        Update tier prices dynamically
        
        Args:
            prices: List of 6 prices for each tier
            vat: VAT rate (0.08 = 8%)
        """
        if prices and len(prices) == 6:
            for i, price in enumerate(prices):
                if i < len(self.tiers):
                    # Ensure price is a number, not a list
                    if isinstance(price, (list, tuple)):
                        price = price[0] if len(price) > 0 else 0
                    self.tiers[i]['price'] = int(price)
        
        if vat is not None:
            # Ensure vat is a number
            if isinstance(vat, (list, tuple)):
                vat = vat[0] if len(vat) > 0 else 0.08
            self.vat_rate = float(vat)
    
    def calculate_bill(self, kwh: float) -> dict:
        """
        Calculate electricity bill with tiered pricing
        
        Args:
            kwh: Total electricity consumption in kWh
        
        Returns:
            dict: Detailed bill breakdown
        """
        tier_details = []
        total_before_vat = 0
        remaining_kwh = kwh
        
        for tier in self.tiers:
            if remaining_kwh <= 0:
                break
            
            tier_start = tier['from']
            tier_end = tier['to']
            tier_price = tier['price']
            
            # Ensure tier_price is a number
            if isinstance(tier_price, (list, tuple)):
                tier_price = tier_price[0] if len(tier_price) > 0 else 0
            tier_price = float(tier_price)
            
            # Calculate kWh in this tier
            if tier_end == float('inf'):
                tier_kwh = remaining_kwh
            else:
                tier_range = tier_end - tier_start + 1
                tier_kwh = min(remaining_kwh, tier_range)
            
            tier_cost = tier_kwh * tier_price
            total_before_vat += tier_cost
            
            tier_details.append({
                'tier': tier['tier'],
                'name': tier['name'],
                'kwh': tier_kwh,
                'price': tier_price,
                'cost': tier_cost
            })
            
            remaining_kwh -= tier_kwh
        
        vat_amount = total_before_vat * self.vat_rate
        total_with_vat = total_before_vat + vat_amount
        
        return {
            'total_kwh': kwh,
            'tier_details': tier_details,
            'subtotal': total_before_vat,
            'vat_rate': self.vat_rate,
            'vat_amount': vat_amount,
            'total': total_with_vat
        }
    
    def format_currency(self, amount: float) -> str:
        """Format amount as Vietnamese currency"""
        return f"{amount:,.0f} VNĐ"
    
    def get_bill_summary(self, kwh: float) -> str:
        """Get formatted bill summary"""
        bill = self.calculate_bill(kwh)
        
        lines = []
        lines.append("=" * 40)
        lines.append("    HÓA ĐƠN TIỀN ĐIỆN")
        lines.append("=" * 40)
        lines.append(f"Tổng điện năng: {bill['total_kwh']:.1f} kWh")
        lines.append("-" * 40)
        
        for tier in bill['tier_details']:
            lines.append(f"{tier['name']}")
            lines.append(f"  {tier['kwh']:.1f} kWh x {tier['price']:,} = {self.format_currency(tier['cost'])}")
        
        lines.append("-" * 40)
        lines.append(f"Thành tiền: {self.format_currency(bill['subtotal'])}")
        lines.append(f"VAT ({bill['vat_rate']*100:.0f}%): {self.format_currency(bill['vat_amount'])}")
        lines.append("=" * 40)
        lines.append(f"TỔNG CỘNG: {self.format_currency(bill['total'])}")
        lines.append("=" * 40)
        
        return "\n".join(lines)
    
    def estimate_monthly_cost(self, power_watts: float, hours_per_day: float = 8) -> dict:
        """
        Estimate monthly cost based on current power consumption
        
        Args:
            power_watts: Current power consumption in Watts
            hours_per_day: Average usage hours per day
        
        Returns:
            dict: Estimated monthly consumption and cost
        """
        # Calculate monthly kWh
        daily_kwh = (power_watts / 1000) * hours_per_day
        monthly_kwh = daily_kwh * 30
        
        bill = self.calculate_bill(monthly_kwh)
        
        return {
            'power_w': power_watts,
            'hours_day': hours_per_day,
            'daily_kwh': daily_kwh,
            'monthly_kwh': monthly_kwh,
            'estimated_cost': bill['total']
        }


# Usage tracking for monthly statistics
class UsageTracker:
    """Track electricity usage over time"""
    
    def __init__(self):
        # Usage data: {date: {room_id: kwh}}
        self.daily_usage = {}
        self.monthly_total = 0.0
    
    def add_usage(self, date: str, room_id: int, kwh: float):
        """Add daily usage for a room"""
        if date not in self.daily_usage:
            self.daily_usage[date] = {}
        
        if room_id not in self.daily_usage[date]:
            self.daily_usage[date][room_id] = 0.0
        
        self.daily_usage[date][room_id] += kwh
        self._update_monthly_total()
    
    def _update_monthly_total(self):
        """Update monthly total"""
        self.monthly_total = 0.0
        for date_data in self.daily_usage.values():
            for kwh in date_data.values():
                self.monthly_total += kwh
    
    def get_monthly_total(self) -> float:
        """Get total monthly consumption"""
        return self.monthly_total
    
    def get_room_total(self, room_id: int) -> float:
        """Get total consumption for a room"""
        total = 0.0
        for date_data in self.daily_usage.values():
            total += date_data.get(room_id, 0.0)
        return total
    
    def reset_monthly(self):
        """Reset monthly data"""
        self.daily_usage = {}
        self.monthly_total = 0.0

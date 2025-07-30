import wx


class SerpentinePreviewPanel(wx.Panel):
    """Simple live preview panel that uses the original serpentine calculation"""
    
    def __init__(self, parent):
        super(SerpentinePreviewPanel, self).__init__(parent)
        self.SetBackgroundColour(wx.Colour(255, 255, 255))  # White background
        self.SetMinSize(wx.Size(500, 250))
        
        # Initialize with default parameters
        self.params = {
            "radius": 2, "amplitude": 5, "alpha": 10, "length": 20, "pitch": 0.3,
            "f_wc": 2, "f_width": 0.4, "b_wc": 3, "b_width": 0.2, "noedge": False
        }
        
        self.serpentine_data = None
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        
        # Bind paint event
        self.Bind(wx.EVT_PAINT, self.on_paint)
        self.Bind(wx.EVT_SIZE, self.on_size)
        
        # Initial calculation
        self.update_preview(self.params)
    
    def update_preview(self, params):
        """Update the preview with new parameters using original calculation"""
        self.params = params.copy()
        
        try:
            # Use the original SerpentineVector calculation
            from .serpentine_utils import SerpentineVector
            serpentine = SerpentineVector()
            serpentine.calculate_vectors(self.params)
            self.serpentine_data = serpentine.vectors
            self.calculate_scaling()
            self.Refresh()
        except Exception:
            # If it fails, clear the preview
            self.serpentine_data = None
            self.Refresh()
    
    def calculate_scaling(self):
        """Calculate scaling to fit the pattern in the panel"""
        if not self.serpentine_data:
            return
            
        # Find the bounding box of all segments
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for layer in self.serpentine_data.values():
            for segment in layer['segments']:
                coords = []
                if hasattr(segment, 'x1'):  # LineSeg or Arc
                    coords.extend([segment.x1, segment.y1])
                    if hasattr(segment, 'x2'):
                        coords.extend([segment.x2, segment.y2])
                    if hasattr(segment, 'x3'):  # Arc
                        coords.extend([segment.x3, segment.y3])
                
                if coords:
                    min_x = min(min_x, min(coords[::2]))  # x coordinates
                    max_x = max(max_x, max(coords[::2]))
                    min_y = min(min_y, min(coords[1::2]))  # y coordinates
                    max_y = max(max_y, max(coords[1::2]))
        
        if min_x == float('inf'):
            return
            
        # Calculate scaling to fit in panel with margin
        panel_size = self.GetSize()
        margin = 20
        available_width = panel_size.width - 2 * margin
        available_height = panel_size.height - 2 * margin
        
        pattern_width = max_x - min_x
        pattern_height = max_y - min_y
        
        if pattern_width > 0 and pattern_height > 0:
            scale_x = available_width / pattern_width
            scale_y = available_height / pattern_height
            self.scale_factor = min(scale_x, scale_y, 50.0)  # Cap maximum scale
        else:
            self.scale_factor = 1.0
        
        # Calculate offset to center the pattern
        scaled_width = pattern_width * self.scale_factor
        scaled_height = pattern_height * self.scale_factor
        
        self.offset_x = (panel_size.width - scaled_width) / 2 - min_x * self.scale_factor
        self.offset_y = (panel_size.height - scaled_height) / 2 - min_y * self.scale_factor
    
    def world_to_screen(self, x, y):
        """Convert world coordinates to screen coordinates"""
        screen_x = x * self.scale_factor + self.offset_x
        screen_y = y * self.scale_factor + self.offset_y
        return screen_x, screen_y
    
    def on_size(self, event):
        """Handle panel resize"""
        self.calculate_scaling()
        self.Refresh()
        event.Skip()
    
    def on_paint(self, event):
        """Handle paint events"""
        dc = wx.PaintDC(self)
        self.draw_preview(dc)
    
    def draw_preview(self, dc):
        """Draw the serpentine preview"""
        # Clear the background
        dc.SetBackground(wx.Brush(wx.Colour(255, 255, 255)))
        dc.Clear()
        
        if not self.serpentine_data:
            dc.SetTextForeground(wx.Colour(128, 128, 128))
            dc.DrawText("Preview unavailable", 10, 10)
            return
        
        # Define colors for different layers
        layer_colors = {
            'edgecuts': wx.Colour(128, 128, 128),  # Gray
            'f_copper': wx.Colour(255, 0, 0),      # Red
            'b_copper': wx.Colour(0, 0, 255)       # Blue
        }
        
        # Draw each layer
        for layer_name, layer_data in self.serpentine_data.items():
            if not layer_data['segments']:
                continue
                
            color = layer_colors.get(layer_name, wx.Colour(0, 0, 0))
            pen_width = max(1, min(int(layer_data['width'] * self.scale_factor), 5))
            
            dc.SetPen(wx.Pen(color, pen_width))
            
            for segment in layer_data['segments']:
                if hasattr(segment, 'x1') and hasattr(segment, 'x2') and not hasattr(segment, 'x3'):
                    # Line segment
                    x1, y1 = self.world_to_screen(segment.x1, segment.y1)
                    x2, y2 = self.world_to_screen(segment.x2, segment.y2)
                    dc.DrawLine(int(x1), int(y1), int(x2), int(y2))
                elif hasattr(segment, 'x3'):
                    # Arc - draw as proper arc
                    self.draw_arc(dc, segment)
    
    def draw_arc(self, dc, arc):
        """Draw an arc using the three-point definition"""
        # Convert arc points to screen coordinates
        x1, y1 = self.world_to_screen(arc.x1, arc.y1)
        x2, y2 = self.world_to_screen(arc.x2, arc.y2)  # mid point
        x3, y3 = self.world_to_screen(arc.x3, arc.y3)
        
        # Draw arc as multiple line segments for better curve representation
        # Calculate center and radius from the three points
        try:
            center_x, center_y, radius = self.get_arc_center_radius(x1, y1, x2, y2, x3, y3)
            if radius > 0:
                # Calculate start and end angles
                import math
                start_angle = math.atan2(y1 - center_y, x1 - center_x)
                mid_angle = math.atan2(y2 - center_y, x2 - center_x)
                end_angle = math.atan2(y3 - center_y, x3 - center_x)
                
                # Determine arc direction
                # Check if we go from start to end via mid in counter-clockwise direction
                def normalize_angle(angle):
                    while angle < 0:
                        angle += 2 * math.pi
                    while angle >= 2 * math.pi:
                        angle -= 2 * math.pi
                    return angle
                
                start_norm = normalize_angle(start_angle)
                mid_norm = normalize_angle(mid_angle)
                end_norm = normalize_angle(end_angle)
                
                # Determine if we should go clockwise or counter-clockwise
                # Check if mid point is between start and end in the shorter arc direction
                def angle_between(a1, a2, a3):
                    # Check if a2 is between a1 and a3 going counter-clockwise
                    a1, a2, a3 = normalize_angle(a1), normalize_angle(a2), normalize_angle(a3)
                    if a1 <= a3:
                        return a1 <= a2 <= a3
                    else:
                        return a2 >= a1 or a2 <= a3
                
                if angle_between(start_norm, mid_norm, end_norm):
                    # Counter-clockwise
                    if end_norm < start_norm:
                        end_norm += 2 * math.pi
                    angle_step = (end_norm - start_norm) / 20
                else:
                    # Clockwise
                    if start_norm < end_norm:
                        start_norm += 2 * math.pi
                    angle_step = -(start_norm - end_norm) / 20
                
                # Draw the arc as line segments
                prev_x = x1
                prev_y = y1
                for i in range(1, 21):
                    angle = start_norm + i * angle_step
                    curr_x = center_x + radius * math.cos(angle)
                    curr_y = center_y + radius * math.sin(angle)
                    dc.DrawLine(int(prev_x), int(prev_y), int(curr_x), int(curr_y))
                    prev_x, prev_y = curr_x, curr_y
            else:
                # Fallback to line segments if arc calculation fails
                dc.DrawLine(int(x1), int(y1), int(x2), int(y2))
                dc.DrawLine(int(x2), int(y2), int(x3), int(y3))
        except:
            # Fallback to line segments if anything goes wrong
            dc.DrawLine(int(x1), int(y1), int(x2), int(y2))
            dc.DrawLine(int(x2), int(y2), int(x3), int(y3))
    
    def get_arc_center_radius(self, x1, y1, x2, y2, x3, y3):
        """Calculate the center and radius of an arc from three points"""
        # Handle degenerate cases
        if abs((x2 - x1) * (y3 - y1) - (y2 - y1) * (x3 - x1)) < 1e-10:
            return 0, 0, 0  # Points are collinear
            
        # Use the formula for circle from three points
        D = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
        if abs(D) < 1e-10:
            return 0, 0, 0
            
        ux = ((x1*x1 + y1*y1) * (y2 - y3) + (x2*x2 + y2*y2) * (y3 - y1) + (x3*x3 + y3*y3) * (y1 - y2)) / D
        uy = ((x1*x1 + y1*y1) * (x3 - x2) + (x2*x2 + y2*y2) * (x1 - x3) + (x3*x3 + y3*y3) * (x2 - x1)) / D
        
        import math
        radius = math.sqrt((x1 - ux)**2 + (y1 - uy)**2)
        
        return ux, uy, radius


class PreviewUpdateMixin:
    """Simple mixin to add preview update functionality"""
    
    def setup_preview_updates(self):
        """Setup automatic preview updates when parameters change"""
        # Bind text change events to all parameter text controls
        text_controls = [
            self.r_value, self.a_value, self.alph_value, self.len_value,
            self.pitch_value, self.f_wc_value, self.f_width_value,
            self.b_wc_value, self.b_width_value
        ]
        
        for ctrl in text_controls:
            ctrl.Bind(wx.EVT_TEXT, self.on_parameter_change)
        
        # Bind checkbox change event
        self.edgedisable_value.Bind(wx.EVT_CHECKBOX, self.on_parameter_change)
    
    def on_parameter_change(self, event):
        """Handle parameter changes and update preview"""
        if hasattr(self, 'preview_panel'):
            params = {}
            # Use default values for any invalid parameters
            defaults = {
                "radius": 2, "amplitude": 5, "alpha": 10, "length": 20, "pitch": 0.3,
                "f_wc": 2, "f_width": 0.4, "b_wc": 3, "b_width": 0.2, "noedge": False
            }
            
            for param_name, getter in self.param_getters.items():
                try:
                    value = getter()
                    params[param_name] = value if value is not None else defaults.get(param_name, 0)
                except:
                    params[param_name] = defaults.get(param_name, 0)
            
            self.preview_panel.update_preview(params)
        
        event.Skip()

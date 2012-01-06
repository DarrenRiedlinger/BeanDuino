"""
GP:
Changed datasource, title, and refresh interval to use
as a poor man's Arduino oscilliscope.

This demo demonstrates how to draw a dynamic mpl (matplotlib) 
plot in a wxPython application.

It allows "live" plotting as well as manual zooming to specific
regions.

Both X and Y axes allow "auto" or "manual" settings. For Y, auto
mode sets the scaling of the graph to see all the data points.
For X, auto mode makes the graph "follow" the data. Set it X min
to manual 0 to always see the whole data from the beginning.

Note: press Enter in the 'manual' text box to make a new value 
affect the plot.

Eli Bendersky (eliben@gmail.com)
License: this code is in the public domain
Last modified: 31.07.2008
"""
import os
import pprint
import random
import sys
import wx
import wx.lib.agw.floatspin as FS

REFRESH_INTERVAL_MS = 90

# The recommended way to use wx with mpl is with the WXAgg
# backend. 
#
import matplotlib
matplotlib.use('WXAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_wxagg import \
    FigureCanvasWxAgg as FigCanvas, \
    NavigationToolbar2WxAgg as NavigationToolbar
import numpy as np
import pylab
#Data comes from here
from SerialQueue import SerialData as DataGen


class SetpointBox(wx.Panel):
    """ A static box with two radio buttons and two corresponding
    floatspin text boxes to enter setpoint or rate-of-rise"""
    def __init__(self, parent, ID, label, initval, serial_obj):
	wx.Panel.__init__(self, parent, ID)

	self.ser = serial_obj

	self.value = initval

        box = wx.StaticBox(self, -1, label)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
	
	self.radio_ror = wx.RadioButton(self, -1,
		label="Rate-of-rise", style=wx.RB_GROUP)
	self.radio_sp = wx.RadioButton(self, -1,
		label="Setpoint")
	self.radio_sp.SetValue(True)

        self.ror_text = FS.FloatSpin(self, -1, 
            size=(70,-1),
            value=0,
            style=wx.TE_PROCESS_ENTER,
	    min_val=-500,
	    max_val=500,
	    increment=0.5,
	    digits=1)
	self.sp_text = FS.FloatSpin(self, -1, 
            size=(70,-1),
            value=str(initval),
            style=wx.TE_PROCESS_ENTER,
	    min_val=-500,
	    max_val=550,
	    increment=1.0,
	    digits=1)
        

	#self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_toggle, self.radio_ror)
	self.Bind(wx.EVT_RADIOBUTTON, self.on_radio_toggle, self.radio_sp)

        self.Bind(wx.EVT_UPDATE_UI, self.on_update_ror_text, self.ror_text)
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_sp_text, self.sp_text)

	self.Bind(wx.EVT_TEXT_ENTER, self.on_ror_text_enter, self.ror_text)
        self.Bind(wx.EVT_SPINCTRL, self.on_ror_text_enter, self.ror_text)
       
        self.Bind(wx.EVT_TEXT_ENTER, self.on_sp_text_enter, self.sp_text)
        self.Bind(wx.EVT_SPINCTRL, self.on_sp_text_enter, self.sp_text)
        
        ror_box = wx.BoxSizer(wx.HORIZONTAL)
        ror_box.Add(self.radio_ror, flag=wx.ALIGN_CENTER_VERTICAL)
        ror_box.Add(self.ror_text, flag=wx.ALIGN_CENTER_VERTICAL)
 
	sp_box = wx.BoxSizer(wx.HORIZONTAL)
        sp_box.Add(self.radio_sp, flag=wx.ALIGN_CENTER_VERTICAL)
        sp_box.Add(self.sp_text, flag=wx.ALIGN_CENTER_VERTICAL)
       
        sizer.Add(ror_box, 0, wx.ALL, 10)
        sizer.Add(sp_box, 0, wx.ALL, 10)

        self.SetSizer(sizer)
        sizer.Fit(self)
    
    def on_radio_toggle(self, event):
	self.ror_text.SetValue(0)
	self.ser.write('R0') # (Re)set RoR to 0

    def on_update_ror_text(self, event):
	#self.ror_text.SetValue(0)
	#self.ser.write('R0') # (Re)set RoR to 0
	self.ror_text.Enable(self.radio_ror.GetValue())
	    
    def on_update_sp_text(self, event):
	#self.ror_text.SetValue(0)
	#self.ser.write('R0') # (Re)set RoR to 0
	self.sp_text.Enable(self.radio_sp.GetValue())
	
    def on_ror_text_enter(self, event):
        self.value = self.ror_text.GetValue()
	self.ser.write('R' + str(self.value))

    def on_sp_text_enter(self, event):
        self.value = self.sp_text.GetValue()
	self.ser.write('S' + str(self.value))
        

class PIDBox(wx.Panel):
    """ Three FloatSpin Boxes  """
    def __init__(self, parent, ID, pval, ival, dval, serial_obj):
	wx.Panel.__init__(self, parent, ID)

	self.ser = serial_obj

	self.p = pval
	self.i = ival
	self.d = dval

        box = wx.StaticBox(self, -1, 'PID Tunings')
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        self.p_text = FS.FloatSpin(self, -1, 
            size=(70,-1),
            value=str(pval),
            style=wx.TE_PROCESS_ENTER,
	    min_val=-100,
	    max_val=100,
	    increment=0.1,
	    digits=2,
	    name='Kp')
	self.i_text = FS.FloatSpin(self, -1, 
            size=(70,-1),
            value=str(ival),
            style=wx.TE_PROCESS_ENTER,
	    min_val=-100,
	    max_val=100,
	    increment=0.1,
	    digits=2,
	    name='Ki')
	self.d_text = FS.FloatSpin(self, -1, 
            size=(70,-1),
            value=str(dval),
            style=wx.TE_PROCESS_ENTER,
	    min_val=-100,
	    max_val=100,
	    increment=0.1,
	    digits=2,
	    name='Kd')

        
        #self.Bind(wx.EVT_UPDATE_UI, self.on_update_manual_text, self.manual_text)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_p_text_enter, self.p_text)
        self.Bind(wx.EVT_SPINCTRL, self.on_p_text_enter, self.p_text)
	self.Bind(wx.EVT_TEXT_ENTER, self.on_i_text_enter, self.i_text)
        self.Bind(wx.EVT_SPINCTRL, self.on_i_text_enter, self.i_text)
	self.Bind(wx.EVT_TEXT_ENTER, self.on_d_text_enter, self.d_text)
        self.Bind(wx.EVT_SPINCTRL, self.on_d_text_enter, self.d_text)
        
        manual_box = wx.BoxSizer(wx.HORIZONTAL)
        manual_box.Add(self.p_text, flag=wx.ALIGN_CENTER_VERTICAL)
	manual_box.Add(self.i_text, flag=wx.ALIGN_CENTER_VERTICAL)
	manual_box.Add(self.d_text, flag=wx.ALIGN_CENTER_VERTICAL)
        
        sizer.Add(manual_box, 0, wx.ALL, 10)
        
        self.SetSizer(sizer)
        sizer.Fit(self)
    
    #def on_update_manual_text(self, event):
    #	pass
        #self.manual_text.Enable(self.radio_manual.GetValue())
    
    def on_p_text_enter(self, event):
	self.p = self.p_text.GetValue()
	self.ser.write('P' + str(self.p))
    def on_i_text_enter(self, event):
	self.i = self.i_text.GetValue()
	self.ser.write('I' + str(self.i))
    def on_d_text_enter(self, event):
	self.d = self.d_text.GetValue()
	self.ser.write('D' + str(self.d))
        
    #def manual_value(self):
    #    return self.value

class BoundControlBox(wx.Panel):
    """ A static box with a couple of radio buttons and a text
        box. Allows to switch between an automatic mode and a 
        manual mode with an associated value.
    """
    def __init__(self, parent, ID, label, initval):
        wx.Panel.__init__(self, parent, ID)
        
        self.value = initval
        
        box = wx.StaticBox(self, -1, label)
        sizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        
        self.radio_auto = wx.RadioButton(self, -1, 
            label="Auto", style=wx.RB_GROUP)
        self.radio_manual = wx.RadioButton(self, -1,
            label="Manual")
        self.manual_text = wx.TextCtrl(self, -1, 
            size=(35,-1),
            value=str(initval),
            style=wx.TE_PROCESS_ENTER)
        
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_manual_text, self.manual_text)
        self.Bind(wx.EVT_TEXT_ENTER, self.on_text_enter, self.manual_text)
        
        manual_box = wx.BoxSizer(wx.HORIZONTAL)
        manual_box.Add(self.radio_manual, flag=wx.ALIGN_CENTER_VERTICAL)
        manual_box.Add(self.manual_text, flag=wx.ALIGN_CENTER_VERTICAL)
        
        sizer.Add(self.radio_auto, 0, wx.ALL, 10)
        sizer.Add(manual_box, 0, wx.ALL, 10)
        
        self.SetSizer(sizer)
        sizer.Fit(self)
    
    def on_update_manual_text(self, event):
        self.manual_text.Enable(self.radio_manual.GetValue())
    
    def on_text_enter(self, event):
        self.value = self.manual_text.GetValue()
    
    def is_auto(self):
        return self.radio_auto.GetValue()
        
    def manual_value(self):
        return self.value


class GraphFrame(wx.Frame):
    """ The main frame of the application
    """
    title = "Dorky Darren's DigiRoaster"
    
    def __init__(self):
        wx.Frame.__init__(self, None, -1, self.title)

	self.setpointval = 100.0
        
        self.datagen = DataGen()
	raw_line = self.datagen.next()

	if raw_line:
		xdata, ydata = raw_line
	        self.xdata = [xdata,]
		self.ydata = [ydata,]
	else:
		self.xdata = [0.0,]
		self.ydata = [70.0,]
		
        self.paused = False
        
        self.create_menu()
        self.create_status_bar()
        self.create_main_panel()
        
        self.redraw_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self.on_redraw_timer, self.redraw_timer)        
        self.redraw_timer.Start(REFRESH_INTERVAL_MS)

    def create_menu(self):
        self.menubar = wx.MenuBar()
        
        menu_file = wx.Menu()
        m_expt = menu_file.Append(-1, "&Save plot\tCtrl-S", "Save plot to file")
        self.Bind(wx.EVT_MENU, self.on_save_plot, m_expt)
        menu_file.AppendSeparator()
        m_exit = menu_file.Append(-1, "E&xit\tCtrl-X", "Exit")
        self.Bind(wx.EVT_MENU, self.on_exit, m_exit)
                
        self.menubar.Append(menu_file, "&File")
        self.SetMenuBar(self.menubar)

    def create_main_panel(self):
        self.panel = wx.Panel(self)

        self.init_plot()
        self.canvas = FigCanvas(self.panel, -1, self.fig)

        self.xmin_control = BoundControlBox(self.panel, -1, "X min", 0)
        self.xmax_control = BoundControlBox(self.panel, -1, "X max", 20)
        self.ymin_control = BoundControlBox(self.panel, -1, "Y min", 0)
        self.ymax_control = BoundControlBox(self.panel, -1, "Y max", 500)

	self.setpoint_control = SetpointBox(self.panel, -1, "Setpoint", 100,
			serial_obj = self.datagen.ser)

	self.pid_control = PIDBox(self.panel, -1, 
			pval=10, 
			ival=2, 
			dval=0.05,
			serial_obj = self.datagen.ser)
        
        self.pause_button = wx.Button(self.panel, -1, "Pause")
        self.Bind(wx.EVT_BUTTON, self.on_pause_button, self.pause_button)
        self.Bind(wx.EVT_UPDATE_UI, self.on_update_pause_button, self.pause_button)
        
 
	self.cb_grid = wx.CheckBox(self.panel, -1, 
            "Show Grid",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_grid, self.cb_grid)
        self.cb_grid.SetValue(True)
        
        self.cb_xlab = wx.CheckBox(self.panel, -1, 
            "Show X labels",
            style=wx.ALIGN_RIGHT)
        self.Bind(wx.EVT_CHECKBOX, self.on_cb_xlab, self.cb_xlab)        
        self.cb_xlab.SetValue(True)
        
        self.hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox1.Add(self.pause_button, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        self.hbox1.AddSpacer(20)
        self.hbox1.Add(self.cb_grid, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        self.hbox1.AddSpacer(10)
        self.hbox1.Add(self.cb_xlab, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        
        self.hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        self.hbox2.Add(self.xmin_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.xmax_control, border=5, flag=wx.ALL)
        self.hbox2.AddSpacer(24)
        self.hbox2.Add(self.ymin_control, border=5, flag=wx.ALL)
        self.hbox2.Add(self.ymax_control, border=5, flag=wx.ALL)
	self.hbox2.Add(self.setpoint_control, border=5, flag=wx.ALL)
	
	self.hbox3 = wx.BoxSizer(wx.HORIZONTAL)
	self.hbox3.Add(self.pid_control, border=5, flag=wx.ALL | wx.ALIGN_CENTER_VERTICAL)
        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(self.canvas, 1, flag=wx.LEFT | wx.TOP | wx.GROW)        
        self.vbox.Add(self.hbox1, 0, flag=wx.ALIGN_LEFT | wx.TOP)
        self.vbox.Add(self.hbox2, 0, flag=wx.ALIGN_LEFT | wx.TOP)
	self.vbox.Add(self.hbox3, 0, flag=wx.ALIGN_LEFT | wx.TOP)
        
        self.panel.SetSizer(self.vbox)
        self.vbox.Fit(self)
    
    def create_status_bar(self):
        self.statusbar = self.CreateStatusBar()

    def init_plot(self):
        self.dpi = 100
        self.fig = Figure((3.0, 3.0), dpi=self.dpi)

        self.axes = self.fig.add_subplot(111)
        self.axes.set_axis_bgcolor('black')
        self.axes.set_title("Dorky Darren's Digi-Roaster", size=12)
        
        pylab.setp(self.axes.get_xticklabels(), fontsize=8)
        pylab.setp(self.axes.get_yticklabels(), fontsize=8)

        # plot the data as a line series, and save the reference 
        # to the plotted line series
        #
        self.plot_data = self.axes.plot(
            self.xdata,
	    self.ydata,
            linewidth=1,
            color=(1, 1, 0),
            )[0]

    def draw_plot(self):
        """ Redraws the plot
        """
        # when xmin is on auto, it "follows" xmax to produce a 
        # sliding window effect. therefore, xmin is assigned after
        # xmax.
        #
        if self.xmax_control.is_auto():
            xmax = round(self.xdata[-1], 0) + 1 if round(self.xdata[-1], 0) + 1 > 20 else 20
        else:
            xmax = int(self.xmax_control.manual_value())
            
        if self.xmin_control.is_auto():            
            xmin = xmax - 20
        else:
            xmin = int(self.xmin_control.manual_value())

        # for ymin and ymax, find the minimal and maximal values
        # in the data set and add a mininal margin.
        # 
        # note that it's easy to change this scheme to the 
        # minimal/maximal value in the current display, and not
        # the whole data set.
        # 
        if self.ymin_control.is_auto():
            ymin = round(min(self.ydata), 0) - 1
        else:
            ymin = int(self.ymin_control.manual_value())
        
        if self.ymax_control.is_auto():
            ymax = round(max(self.ydata), 0) + 1
        else:
            ymax = int(self.ymax_control.manual_value())

        self.axes.set_xbound(lower=xmin, upper=xmax)
        self.axes.set_ybound(lower=ymin, upper=ymax)
        
        # anecdote: axes.grid assumes b=True if any other flag is
        # given even if b is set to False.
        # so just passing the flag into the first statement won't
        # work.
        #
        if self.cb_grid.IsChecked():
            self.axes.grid(True, color='gray')
        else:
            self.axes.grid(False)

        # Using setp here is convenient, because get_xticklabels
        # returns a list over which one needs to explicitly 
        # iterate, and setp already handles this.
        #  
        pylab.setp(self.axes.get_xticklabels(), 
            visible=self.cb_xlab.IsChecked())
        
        self.plot_data.set_xdata(np.array(self.xdata))
        self.plot_data.set_ydata(np.array(self.ydata))
        
        self.canvas.draw()
    
    def on_pause_button(self, event):
        self.paused = not self.paused
    
    def on_update_pause_button(self, event):
        label = "Resume" if self.paused else "Pause"
        self.pause_button.SetLabel(label)
    
    def on_cb_grid(self, event):
        self.draw_plot()
    
    def on_cb_xlab(self, event):
        self.draw_plot()
    
    def on_save_plot(self, event):
        file_choices = "PNG (*.png)|*.png"
        
        dlg = wx.FileDialog(
            self, 
            message="Save plot as...",
            defaultDir=os.getcwd(),
            defaultFile="plot.png",
            wildcard=file_choices,
            style=wx.SAVE)
        
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.canvas.print_figure(path, dpi=self.dpi)
            self.flash_status_message("Saved to %s" % path)
    
    def on_redraw_timer(self, event):
        # if paused do not add data, but still redraw the plot
        # (to respond to scale modifications, grid change, etc.)
        #
        if not self.paused:
	    raw_line = self.datagen.next()
	    if raw_line:
		xdata, ydata = raw_line
	        self.xdata.append(xdata)
		self.ydata.append(ydata)
        
       		self.draw_plot()
		self.flash_status_message("Temp: %s" % self.ydata[-1],
			flash_len_ms=REFRESH_INTERVAL_MS)
    
    def on_exit(self, event):
        self.Destroy()
    
    def flash_status_message(self, msg, flash_len_ms=1500):
        self.statusbar.SetStatusText(msg)
        self.timeroff = wx.Timer(self)
        self.Bind(
            wx.EVT_TIMER, 
            self.on_flash_status_off, 
            self.timeroff)
        self.timeroff.Start(flash_len_ms, oneShot=True)
    
    def on_flash_status_off(self, event):
        self.statusbar.SetStatusText('')


if __name__ == '__main__':
    app = wx.PySimpleApp()
    app.frame = GraphFrame()
    app.frame.Show()
    app.MainLoop()


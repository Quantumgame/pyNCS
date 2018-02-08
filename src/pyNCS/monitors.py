#-----------------------------------------------------------------------------
# Purpose:
#
# Author: Emre Neftci
#
# Copyright : University of Zurich, Giacomo Indiveri, Emre Neftci, Sadique Sheik, Fabio Stefanini
# Licence : GPLv2
#-----------------------------------------------------------------------------

import numpy as np
import pylab
from collections import defaultdict
from .pyST.STsl import mapSpikeListAddresses, composite_plot, SpikeList, SpikeTrain, merge_spikelists
import copy

def create_SpikeMonitor_from_SpikeList(st):
    '''
    Creates a channel spikelist dictionary from a spikelist or a list of spikelists 
    '''
    from pyNCS import AddrGroupBase
    msl = monitorSpikeList(0, st)
    a = AddrGroupBase('')
    a.paddr = a.laddr = a.addr = st.id_list()
    a.channel = 0
    sm = SpikeMonitor(addr_group = a)
    sm.populate(msl)
    return sm
    

class Monitors(object):
    """
    A container for SpikeMonitors.
    This object is automatically generated by NeuroSetup as neurosetup.monitors
    """
    def __init__(self):
        self.monitors = []
        self.__class__.get_t_start = get_t_start
        self.__class__.get_t_stop = get_t_stop

    def __iter__(self):
        for mon in self.monitors:
            yield mon

    def __len__(self):
        return len(self.monitors)

    def __getitem__(self, item_id):
        return self.monitors[item_id]

    def __setitem__(self, item_id, item):
        self.monitors[item_id] = item

    def append(self, spikemonitor):
        if not isinstance(spikemonitor, SpikeMonitor):
            raise TypeError('Can only append a object of type SpikeMonitor')

    def to_chstlist(self):
        '''
        Returns a dictionary with channels as keys and merged SpikeLists as values.
        '''
        chstlist = defaultdict(SpikeList)
        for spk_mon in self:
            chstlist[spk_mon.channel] = merge_spikelists(spk_mon.sl,chstlist[spk_mon.channel])
        return chstlist

    @property
    def channels(self):
        '''
        Returns a list of channels monitored by the current SpikeMonitors
        '''
        chan_mon = np.unique([mon.channel for mon in self])
        if len(chan_mon) == 0:
            chs = None
        else:
            chs = chan_mon
        return chs

    def normalize_tstart_tstop(self, t_stop=None):
        #Search for t_stop if not provided
        if t_stop == None:
            t_stop = 0
            for m in self:
                if m.sl.t_stop > t_stop:
                    t_stop = m.sl.t_stop

        for m in self:
            if not m.sl.t_stop > t_stop:
                m.sl.t_stop = t_stop

    def populate(self, chstlist):
        """
        Populates SpikeMonitors in the list of monitors
        chstlist is the dictionary returned by NeuroSetup.stimulate.
        (this is also the object that channelAddressing.rawoutput_from_chevents returns (a RawOutput object)

        """
        for mon, st in self.iterchst(chstlist):
            mon.populate(st)

    def populate_monitors(self, chstlist):
        '''
        backward compatibility
        '''
        return self.populate(chstlist)

    def iterchst(self, chstlist):
        """
        iterate over channels in monitors and try to find spikelists with matching channels.
        """
        for mon in self:
            try:
                yield mon, chstlist[mon.channel]
            except KeyError:
                pass

    def import_monitors(self, monitors, append=True):
        """
        Import SpikeMonitors to setup.
        monitors: append a SpikeMonitor object or a list of them (replace if append=False)
        """
        if not hasattr(monitors, "__iter__"):
            monitors = [monitors]

        for m in monitors:
            if not isinstance(m, SpikeMonitor):
                raise TypeError("monitors is not a SpikeMonitor or a list of SpikeMonitors")

        if append == True:
            self.monitors += monitors
        else:
            self.monitors = monitors
        return None

    def import_monitors_otf(self, populations, synapse=None, append=True):
        '''
        Same as create
        '''
        if not hasattr(populations, "__iter__"):
            populations = [populations]

        monitors_new = []
        for pop in populations:
            if synapse == None:
                monitors_new.append(SpikeMonitor(pop.soma))
            else:
                monitors_new.append(SpikeMonitor(pop.synapses[synapse]))

        if append == True:
            self.monitors += monitors_new
        else:
            self.monitors = []
            self.monitors += monitors_new

        return monitors_new

    def create(self, populations, synapse=None, append=True):
        """
        Create monitors and import SpikeMonitors to setup.
        monitors: append a SpikeMonitor object or a list of them
        if synapse is None, then the soma is taken as the address group to monitor, otherwise the synapse is taken for all the populations
        """
        return self.import_monitors_otf(populations, synapse=None, append=True)

    def iter_spikelists(self):
        for mon in self:
            yield mon.sl

    def iter_remapped_spikelists(self):
        for i, mon in enumerate(self):
            yield mon.get_remapped_spikelist(
                    s_start=float(i),
                    s_stop=float(i))

    def raster_plot(self, *args, **kwargs):
        """
        Raster Plotting tool which can handle plotting several SpikeLists/ SpikeMonitors/ monitorSpikeLists
        """
        return RasterPlot(self, *args, **kwargs)
    
    def rate_plot(self, *args, **kwargs):
        """
        Rate Plotting tool which can handle plotting several SpikeLists/ SpikeMonitors/ monitorSpikeLists
        """
        return MeanRatePlot(self, *args, **kwargs)

    #def composite_plot(self,*args,**kwargs):
    #    """
    # Raster Plotting tool which can handle plotting several SpikeLists/
    # SpikeMonitors/ monitorSpikeLists
    #    """
    #    h,ha=self.__create_multifigure()
    #    kwargs['display']=ha
    #    for st in self.__iter_remapped_spikelists():
    #        st.composite_plot(*args,**kwargs)
    #    self.__post_process_multifigure(h,ha)


def get_t_start(self):
    """
    Iterates over all spikelists in Monitors and returns t_start
    """
    t_start = 2 ** 16 - 1.
    for st in self.iter_spikelists():
        t_start = min(st.t_start, t_start)
    return t_start


def get_t_stop(self):
    """
    Iterates over all spikelists in Monitors and returns t_stop
    """
    t_stop = 0.0
    for st in self.iter_spikelists():
        t_stop = max(st.t_stop, t_stop)
    return t_stop


class PlotBase(object):
    """
    Base Class for plotting SpikeMonitors.
    Virtual class, use RasterPlot or MeanRatePlot instead.
    """

    def __init__(self, monitors):
        self.__class__.get_t_start = get_t_start
        self.__class__.get_t_stop = get_t_stop

        if isinstance(monitors, SpikeList):
            mons = create_SpikeMonitor_from_SpikeList(monitors)  
            self.monitors = mons   
        elif not hasattr(monitors, '__iter__'):
            mons = [monitors]
            self.monitors = mons
        else:
            self.monitors = monitors
        self.h, self.ha = self.create_multifigure()

    def __iter__(self):
        for mon in self.monitors:
            yield mon

    def __len__(self):
        return len(self.monitors)

    def iter_spikelists(self):
        """
        Iterates over spikelists in every SpikeMonitor in monitors
        """
        for mon in self:
            yield mon.sl

    def iter_remapped_spikelists(self, sminmax = [.1, .9]):
        """
        Iterates over spikelists in monitors and return a spikelist whose addresses are remapped according to position in monitors. Yields a SpikeMonitorTrain object
        """
        for st, mon, i in self.iter_remapped(sminmax):
            return st

    def iter_remapped(self, sminmax = [.1, .9]):
        """
        Iterates over spikelists in monitors and return a spikelist whose addresses are remapped according to position in monitors. Yields a SpikeMonitor object
        """
        if sminmax is not None:
            for i, mon in enumerate(self):
                yield mon.get_remapped_spikelist(
                        s_start=float(i + sminmax[0]),
                        s_stop=float(i + sminmax[1])),\
                        mon,\
                        i,\
                        i+.5
        else:
            ll = [0]
            for i, mon in enumerate(self):
                ll.append(max(mon.sl.id_list())-min(mon.sl.id_list()))
            ll = np.cumsum(ll)
            ll /= ll.max() / len(self)
            for i, mon in enumerate(self):
                print((ll[i], ll[i+1]))
                yield mon.get_remapped_spikelist(
                        s_start=float(ll[i]),
                        s_stop=float(ll[i+1])),\
                        mon,\
                        i,\
                        (ll[i]+ll[i+1])/2



    def create_multifigure(self):
        """
        Create base figure
        """
        h = pylab.figure()
        ha = pylab.axes()
        return h, ha

    def post_process_multifigure(self):
        pass

    def draw(self):
        pass


import matplotlib.ticker as mticker


class LinearTickLocator(mticker.MaxNLocator):
    def __init__(self, *args, **kwargs):
        mticker.MaxNLocator.__init__(self, *args, **kwargs)

    def __call__(self, *args, **kwargs):
        return mticker.MaxNLocator.__call__(self, *args, **kwargs)


class RasterPlot(PlotBase):
    """
    A Raster Plot Class for plotting several Spike Monitors at once.
    The figure is automatically plotted, unless it is constructed with plot=False.
    Inputs: 
    *flat* : if true, the spike lists are flattened before plotting
    *even_distance* : if true, the distance between the rasters is fixed.
    plot_kwargs is passed to the final matplotlib plotting function.
    kwargs are passed to raster_plot
    """

    def __init__(self, monitors, flat=False, even_distance = False, plot_kwargs={}, *args, **kwargs):
        PlotBase.__init__(self, monitors)
        self.flat = flat
        self.even = even_distance
        self.cs = []  #centers of raster plots


        self.draw(plot_kwargs, *args, **kwargs)
        self.post_process_multifigure()

    def post_process_multifigure(self):
        """
        Sets ylim, labels and ticks
        """
    
        self.ha.set_xlim([0., self.get_t_stop()])
        self.ha.set_ylabel('Population')
        self.ha.set_xlabel('Time [ms]')
        self.ha.set_ylim([0., len(self)])
        self.__set_yticks()
        pylab.draw()

    def __set_yticks(self):
        """
        Set tick labels to self.addr_group names.
        """
        fr = []
        to = []
        for i, mon in enumerate(self):
            fr.append(self.cs[i])
            to.append(mon.get_short_name())
        pylab.yticks(fr, to, rotation=90)


    def draw(self, plot_kwargs={}, *args, **kwargs):
        """
        Draws the raster plot.
        """
        for i in range(len(self)):
            if not self.even: self.ha.axhline(float(i + 1), linewidth=2, alpha=0.2)
        kwargs.setdefault('display', self.ha)
        if self.even == True:
            sminmax = None
        else:
            sminmax= [0.05,.95]
        self.cs = []
        for st, mon, i, c  in self.iter_remapped(sminmax):
            self.cs.append(c)
            plot_kwargs_mon = mon.get_plotargs(plot_kwargs)
            if not self.flat:
                st.raster_plot(kwargs=plot_kwargs_mon, *args, **kwargs)
            else:
                st.raster_plot_flat(
                    id=i + 0.5, kwargs=plot_kwargs_mon, *args, **kwargs)


class MeanRatePlot(PlotBase):
    """
    A Mean Rate Plot with plots the mean rates of the provided SpikeMonitors.
    The figure is automatically plotted
    """

    def __init__(self, monitors, time_bin=30, mean=True, *args, **kwargs):
        """
        *monitors*: an iterable which contains SpikeMonitors
        *time_bin*: time bin which will be used to compute the firing rates
        *args* and *kwargs* will be passed to pylab.plot
        """
        PlotBase.__init__(self, monitors)

        self.time_bin = int(time_bin)
             #If this is set to float, then y scale gets screwed. No idea why!
        self.max_rate = 0.
        self.mean = mean
        self.draw(*args, **kwargs)
        self.post_process_multifigure()

    def post_process_multifigure(self):
        """
        Sets ylim, labels and ticks
        """
        self.ha.set_ylim([0., self.max_rate])
        self.ha.set_xlim([0., self.get_t_stop()])
        self.ha.set_ylabel('Mean Firing Rate [Hz]')
        self.ha.set_xlabel('Time [ms]')
        self.ha.legend()
        pylab.draw()

    def draw(self, *args, **plot_args):
        """
        Plot the mean rate of each SpikeMonitor over time.
        """
        plot_args.setdefault('alpha', 0.8)
        plot_args.setdefault('linewidth', 2.)
        labels_dict = dict()
        for i, mon in enumerate(self):
            #get mean rate
            mr = mon.firing_rates(time_bin=self.time_bin, mean=self.mean)
            self.max_rate = max(self.max_rate, max(mr))
            t = mon.sl.time_axis(time_bin=self.time_bin)[:-1]
            plot_args_mon = mon.get_plotargs(plot_args)
            labelname = mon.get_short_name()
            if not labelname in labels_dict:
                plot_args_mon.setdefault('label', labelname)
                labels_dict[labelname] = True

            self.ha.plot(t,
                    mr,
                    *args,
                    **plot_args_mon)


class SpikeMonitor(object):
    """
    A class for monitoring spiking activity during experimentation.
    Interface is similar to the one of AddrGroup.

    >>> pop_mon = SpikeMonitor(pop.soma, plot_args={'color':'r', 'linewidth':3})
    >>> nsetup.monitors.import_monitors([pop_mon])
    >>> nsetup.stimulate(stStim)
    >>> nsetup.monitors.raster_plot()

    """
    def __init__(self, addr_group=None, plot_args = None):
        # By definition of populations, SpikeMonitor is associated to at most
        # one channel
        self.addr_group = addr_group
        if plot_args == None:
            self.plot_args = {}
        else:
            self.plot_args = plot_args
        self._sl = monitorSpikeList(self.addr_group.channel,
             spikes=[], id_list=np.sort(addr_group.laddr))
        self._populated = False
        self.name = self.addr_group.name
        self.channel = self.addr_group.channel

    def create_spiketrains(self, name, *args, **kwargs):
        '''
        Create spike trains from addr_group.
        Inputs:
        *name*: specifies spiketrains type. Function calls 'addr_group.spiketrains_'+name
        **args* and ***kwargs* passed to spiketrains_+name function
        '''
        self._sl = self.to_monitorSpikeList(getattr(self.addr_group,'spiketrains_'+name)(*args,**kwargs)[self.channel])

    @property
    def sl(self):
        """
        SpikeList of the monitor. The SpikeList is constructed Just in Time.
        """
        if not self._populated and hasattr(self, '_data'):
            self._do_populate()
            return self._sl
        else:
            return self._sl

    def __len__(self):
        return self.addr_group.__len__()

    def __getslice__(self, i, j):
        #TODO: consider returning slices monitor instead
        return self.addr_group.__getslice__(i, j)

    def copy(self):
        '''
        Returns a copy of the SpikeMonitor
        '''
        s = SpikeMonitor(copy.copy(self.addr_group))
        s.populate(self.sl)
        return s

    def get_short_name(self):
        """
        Get first word of self.name, used for labels in raster plot.
        """
        return self.name.split(' ')[0]

    def populate(self, st):
        """
        Populate SpikeMonitor with monitered events
        """
        self._data = st
        self._populated = False

    def _do_populate(self):
        assert hasattr(self, '_data'), "SpikeMonitor must be populated first"
        self._populated = True
        self._sl = self.to_monitorSpikeList(self._data)
        self._sl.complete(self.addr_group.laddr)
        del self._data

    def get_normalized_addr(self, s_start=0.0, s_stop=1.0):
        """
        Return a an address list with the spikelist addresses mapped linearly to the interval (s_start, s_stop)
        """
        return self.__normalize_addr(s_start, s_stop)

    def __normalize_addr(self, s_start=0.0, s_stop=1.0):
        N = len(self)
        new_addrset = np.linspace(s_start, s_stop, N)
        return new_addrset

    def get_remapped_spikelist(self, s_start=0.0, s_stop=1.0):
        """
        Return a spikelist whose addresses are mapped linearly to the interval (s_start, s_stop)
        """
        mapping = dict(list(zip(
            self.addr_group.laddr, self.get_normalized_addr(s_start, s_stop))))
        return self.sl.id_list_map(mapping)

    def raster_plot(self, plot_kwargs={}, *args, **kwargs):
        """
        Raster plot of the spikelist. plot_kwargs is passed to the plot in raster_plot, whereas kwargs and args are passed to raster_plot.
        """
        plot_kwargs_mon = self.get_plotargs(plot_kwargs)
        self.sl.raster_plot(kwargs=plot_kwargs_mon, *args, **kwargs)

    def composite_plot(self, *args, **kwargs):
        """
        Composite plot of the spikelist. plot_kwargs is passed to the plot in raster_plot, whereas kwargs and args are passed to raster_plot.
        """
        self.set_plotargs(kwargs)
        self.sl.composite_plot(*args, **kwargs)

    def set_plotargs(self, kwargs):
        """
        Changes plot arguments. Existing plot_args are not removed.
        """
        self.plot_args.update(self.get_plotargs(kwargs))

    def get_plotargs(self, kwargs={}):
        """
        Get plot arguments according to SpikeMonitor's default. 
        Optionally, kwargs can be passed: these are added to the plot argumetns, but does not save them.
        """
        plot_kwargs_mon = kwargs.copy()
        for k, v in self.plot_args.items():
            plot_kwargs_mon.setdefault(k, v)
        return plot_kwargs_mon

    def to_monitorSpikeList(self, st):
        """
        Transform SpikeList *st* into a monitorSpikeList object
        """
        adtm = np.fliplr(st.raw_data())
        if adtm.shape[0] == 0:
            return monitorSpikeList(channel=None, spikes=[], id_list=[])
        t_start, t_stop = min(adtm[:, 1]), max(adtm[:, 1])
        return monitorSpikeList(self.addr_group.channel, spikes=adtm, id_list=np.sort(self.addr_group.laddr), t_start=t_start, t_stop=t_stop)

    def mean_rate(self, t_start=None, t_stop=None):
        return self.sl.mean_rate(t_start=t_start, t_stop=t_stop)

    def firing_rates(self, time_bin=30, mean=True, offset=None):
        st = self.sl
        #get mean rate
        st = self.sl
        if not offset == None:
            st = st.copy()
            st.time_offset(offset)
        m = st.firing_rate(time_bin=time_bin, average=True)
        if not mean:
            m = m * len(st)
        return m


class monitorSpikeList(SpikeList):
    """
    A wrapper for the NeuroTools SpikeList
    """
    def __init__(self, channel, *args, **kwargs):
        self.channel = channel
        super(monitorSpikeList, self).__init__(*args, **kwargs)

    def id_list_map(self, mapping):
        '''
        this function maps the addresses of a spike list into another using the given mapping. Useful for logical to physical translation and vice versa
        SL=original spike list
        mapping=dictionary containing address mapping
        '''
        mapped_SL = monitorSpikeList(self.channel, spikes=[], id_list=[])
        addr_SL = self.id_list()
        for k, v in mapping.items():
            if k in addr_SL:
                try:
                    mapped_SL[v] = self[k]
                except KeyError:
                    pass

        all_others = np.setdiff1d(self.id_list(), list(mapping.keys()))
        for k in all_others:
            mapped_SL[k] = self[k]

        return mapped_SL

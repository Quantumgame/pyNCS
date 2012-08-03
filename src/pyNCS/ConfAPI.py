#-----------------------------------------------------------------------------
# Purpose:
#
# Author: <authors name>
#
# Copyright : University of Zurich, Giacomo Indiveri, Emre Neftci, Sadique Sheik, Fabio Stefanini
# Licence : GPLv2
#-----------------------------------------------------------------------------
#ConfAPI
#Biases and mapper
#Api for modules having pyAMDA-like functionality
#Api for modules having pyAEX-like functionality

from ComAPI import ResourceManagerBase, BatchCommunicatorBase
from types import GeneratorType  # For checking generator type
from contextlib import contextmanager
from lxml import etree
import warnings

# Traits imports
try:
    from enthought.traits.api import *
    from enthought.traits.ui.api import *
except ImportError:
    from traits.api import *
    from traitsui.api import *


class Parameter(HasTraits):
    SignalName = Str('Parameter name')  # Parameter name
    _onlyGui = False  # Flag to only update GUI
    v = Property(Range(-1., 3.3))
    _v = None

    def _get_v(self):
        if self._v is None:
            self._v = self.getValue()
        return self._v

    def _set_v(self, value):
        if not self._onlyGui:
            self.setValue(value)
        else:
            self._v = value

    view = View(Group(Item('SignalName', style='readonly',
                           show_label=False),
                      Item('v', show_label=False, resizable=True),
                      orientation='horizontal'),
                resizable=True,
               )

    def __init__(self, parameters, configurator):
        '''
        Parameter(parameters, configurator)
        parameters: dictionary of parameters and values
        This object is designed to be used with the configurator to set parameters
        '''
        self.params = dict(parameters)
        self.configurator = configurator
        # Initialize variable for GUI
        self.SignalName = self.params['SignalName']

    def __str__(self):
        return str(self.params)

    def __getXML__(self):
        '''
        Returns lxml.etree.Element representatoin of this parameter
        '''
        doc = etree.Element('parameter')
        for n, v in self.params.items():
            doc.attrib[n] = str(v)
        return doc

    def __parseXML__(self, doc):
        '''
        Parse xml file or element tree to generate the object
        '''
        if isinstance(doc, str):
            # parse the file
            doc = etree.parse(doc).getroot()
        else:
            # assuming doc is an lxml Element object.
            assert doc.tag == 'parameter'
        self.params = dict(doc.attrib)
        for k, v in self.params.items():
            try:
                v = float(v)
            except:
                pass
            self.params[k] = v
        self.SignalName = self.params['SignalName']

    def getValue(self):
        return self.configurator.get_parameter(self.params['SignalName'])

    def setValue(self, value):
        x = self.configurator.set_parameter(self.params['SignalName'], value)
        self._v = x  # Update gui
        return x


class ConfiguratorBase(ResourceManagerBase):
    def __init__(self):
        '''
        ConfiguratorBase()
        Base class for managing parameters
        Contains functions
        - set_parameter (required)
        - get_parameter (required)
        - add_parameter (required)
        - get_parameter_names (required)
        - reset (required)
        - set_parameters (optional)
        - get_parameters (optional)
        - context_get_param (optional)

        Parameters should be stored in the _parameter dictionary.
        The dictionary's keys should be the parameter names.
        Inherits ResourceManagerBase
        '''
        self.parameters = {}
        self._neurosetup = None
        self._neurosetup_registered = False
        ResourceManagerBase.__init__(self)

    @property
    def neurosetup(self):
        if not self._neurosetup_registered:
            warnings.warn('NeuroSetup has not been registered')
            return None
        else:
            return self._neurosetup

    def register_neurosetup(self, neurosetup):
        '''
        Provides a link to the Neurosetup. This is useful for complex parameter
        configuration protocols requiring the sequencing and monitoring of
        address-events
        '''
        self._neurosetup_registered = True
        self._neurosetup = neurosetup

    def _readCSV(self, CSVfile):
        '''
        Parse the CSV file to build the configurator object.
        '''
        with open(CSVfile, 'r') as CSV:
            csv = CSV.readlines()

        #The following builds bias representations only
        tableFlag = False
        for line in csv:
            line = line.replace('\'', '')  # remove single and double quotes
            line = line.replace('"', '')
            if line.startswith('\t') or line.startswith('\n'):
                tableFlag = False
            elif 'signal' in line.lower() and not tableFlag:
                # TODO: This code assumes that signal is an essential part of
                # table
                # WARNING: There should be some intelligent way to do this!
                tableFlag = True
                tableFields = line.strip().split('\t')
            elif tableFlag and line.strip():
                row = line.strip().split('\t')
                # WARNING: This only works if the word bias exists as a field
                if row[tableFields.index('BiasType')]:
                    parameters = {}
                    for i in range(len(row)):
                        val = row[i]
                        # Check if the string is a number
                        try:
                            val = float(val)
                        except:
                            pass
                        parameters[tableFields[i]] = val
                    self.add_parameter(parameters)
        return

    def __getXML__(self):
        doc = etree.Element('parameters')
        for p in self.parameters.values():
            doc.append(p.__getXML__())
        return doc

    def __parseXML__(self, doc):
        '''
        Parse xml file or element tree to generate the object
        '''
        if isinstance(doc, str):
            # parse the file
            doc = etree.parse(doc).getroot()
        else:
            # assuming doc is an lxml Element object.
            assert doc.tag == 'parameters'
        for param in doc:
            self.add_parameter(param)

    def add_parameter(self, param):
        #IMPLEMENT
        '''
        Add a parameter to the configurator
        param: dictionary with all attributes of parameter or an xml element or
        file name with the <parameter /> element
        '''
        if isinstance(param, dict):
            self.parameters[param['SignalName']] = Parameter(param, self)
        elif isinstance(param, etree._Element):
            parameter = Parameter({'SignalName': ''}, self)
            parameter.__parseXML__(param)
            self.parameters[parameter.SignalName] = parameter

    def get_parameter(self, param_name):
        #IMPLEMENT
        '''
        Gets parameter param_name.
        '''
        return None

    def get_parameters(self, param_names=None):
        #CONVENIENCE FUNCTION. IMPLEMENTATION IS NOT REQUIRED
        '''
        Returns parameters (dictionary of name-value pairs).
        Input:
        *param_names:* A list of parameter names
        If param_names is None, then this function returns all the parameters
        (using self.get_param_names())
        '''
        if param_names is None:
            param_names = self.get_param_names()

        if not isinstance(param_names, (list, tuple, GeneratorType)):
            raise TypeError('param_names should be a list, tuple or generator, not {0}'.
                format(type(param_names)))

        b = dict()
        for i, name in enumerate(param_names):
            b[name] = self.get_parameter(name)
        return b

    def set_parameter(self, param_name, param_value):
        #IMPLEMENT
        '''
        Sets parameter param_name with param_value
        '''
        return None

    def set_parameters(self, param_dict):
        #CONVENIENCE FUNCTION. IMPLEMENTATION IS NOT REQUIRED
        '''
        Set several parameters using a dictionary.
        Input:
        *param_dict*: dictionary of parameter names (str) - value (float) pairs.
        '''
        for name, value in param_dict.iteritems():
            self.set_parameter(name, value)
        return self.get_parameters(param_dict.keys())

    def update_parameter(self, param_name, param_value):
        #CONVENIENCE FUNCTION. IMPLEMENTATION NOT REQUIRED
        '''
        Update/Inform the object of changes made from other clients.
        Input:
            *param_name*: Parameter name
            *param_value*: Parameter value
        Ideal to use when the parameters can be changed from multiple clients
        simultaneously.
        '''
        self.parameters[param_name].v = param_value
        return

    def get_param_names(self):
        #CONVENIENCE FUNCTION. IMPLEMENTATION IS NOT REQUIRED
        '''
        Returns names of all the parameters
        '''
        return self.parameters.keys()

    def save_parameters(self, filename, *kwargs):
        #CONVENIENCE FUNCTION. IMPLEMENTATION IS NOT REQUIRED
        '''
        Saves parameters to a file
        '''
        d = self.get_parameters()
        with open(filename, 'w') as f:
            f.write("\n".join(["%s\t%.17e" % (k, v) for k, v in d.items()]))
        print 'Parameters have been saved to the file %s' % filename
        return None

    def reset(self):
        #IMPLEMENT
        '''
        Resets all the parameters to default values
        '''
        return None

    @contextmanager
    def context_get_param(self):
        #CONVENIENCE FUNCTION. IMPLEMENTATION IS NOT REQUIRED
        '''
        Convenience contextmanager:
        Context used when getting parameter object
        '''
        #This implementation raises an informative exception
        try:
            yield
        except KeyError, e:
            raise KeyError('There is no parameter {0} in the configurator'.
                format(e.message))


class MappingsBase(ResourceManagerBase):
    def __init__(self):
        '''
        MappingsBase()
        Base class for managing mappings

        Contains methods:
        - add_mappings() (required)
        - set_mappings(mappings) (optional)
        - get_mappings()
        - clear_mappings()
        - del_mappings() (optional, not used by pyNCS by default)
        '''
        ResourceManagerBase.__init__(self)

    def add_mappings(self, mappings):
        #IMPLEMENT (REQUIRED)
        '''
        Adds *mappings* to the mappings table.

        Inputs:
        *mappings*: a two-dimenstional iterable
        '''
        pass

    def get_mappings(self):
        #IMPLEMENT (REQUIRED)
        '''
        Returns an array representing the mappings
        '''
        return None

    def clear_mappings(self):
        #IMPLEMENT (REQUIRED)
        '''
        Clears the mapping table. No inputs
        '''
        return None

    def set_mappings(self, mappings):
        #CONVIENCE FUNCTION, IMPLEMENTATION NOT REQUIRED
        '''
        Clears the mapping table and adds *mappings* to the mappings table.

        Inputs:
        *mappings*: a two-dimenstional iterable
        '''
        self.clear_mappings()
        self.add_mappings(mappings)

    def del_mappings(self):
        #IMPLEMENT (OPTIONAL)
        '''
        Clears the mapping table. No inputs
        '''
        raise NotImplementedError('del_mappings has not been implemented')

# Default blank initializations
# Override these classes in custom API as required
Configurator = ConfiguratorBase
Mappings = MappingsBase
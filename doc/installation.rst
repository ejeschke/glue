.. _installation:

Installing Glue
===============

There are several ways to install Glue on your computer. We recommend one of the first two options, which greatly simplify of the (sometimes tricky) task of installing QT, Matplotlib, and other libraries that Glue relies on.

.. note :: Currently, Glue is only supported on Python 2.7. Python 3 support is in progress.


Easiest Option (Recommended for Mac users)
------------------------------------------

Mac users with OS X >= 10.7 can download Glue as a `standalone program
<http://mac.glueviz.org>`_.


Easy Option (Recommended for Windows, Unix users)
-------------------------------------------------

We recommend using the `Anaconda
<http://continuum.io/downloads.html>`_ Python distribution from
Continuum Analytics. Anaconda includes all of Glue's main dependencies.

 * Download and install the `appropriate version of Anaconda
   <http://continuum.io/downloads.html>`_

 * On the command line, install Glue using pip: ``pythonw -m pip install glueviz``

 * On the command line, install any additional Glue dependencies by running ``glue-deps install``. For more information on ``glue-deps``, see :ref:`below <glue-deps>`

The `Enthought Python Distribution <https://www.enthought.com/products/epd/>`_ also includes all non-trivial dependencies. The installation instructions are the same.

.. note :: Anaconda installs it's own version of Python

.. _pythonw_note:
.. note :: The nonstandard pip invocation (``pythonw -m pip``) is needed on some OSes with Anaconda, because programs which create graphical windows must be invoked using ``pythonw`` instead of ``python``.

.. warning :: There is currently a `known issue <https://github.com/ContinuumIO/anaconda-issues/issues/63>`_ with running Anaconda's Qt on Kubuntu. `One workaround <http://stackoverflow.com/questions/21212851/anaconda-spyder-qt-library-error-on-launch/21232872#21232872>`_ is to copy the System Qt libraries from ``/usr/lib/x86_64-linux-gnu/libQt*`` to the ``lib`` directory in Anaconda.

Building from Source (For the Brave)
------------------------------------

The source code for Glue is available on `GitHub
<http://www.github.com/glue-viz/glue>`_. Glue relies upon a number of
scientific python libraries, as well as the QT GUI library. Installing
these packages is somewhat beyond the scope of this document, and
unforunately trickier than it should be. If you want to dive in, here
is the basic strategy:

 * Install `Qt 4 <http://qt-project.org/downloads>`_ and either `PyQt4 <http://www.riverbankcomputing.com/software/pyqt/download>`_ or `PySide <http://qt-project.org/wiki/Get-PySide>`_. If at all possible, use the binary installers; building PyQt4 or PySide from source is tricky (this is a euphemism).

 * Install Glue using pip: ``pip install glueviz``. Alternatively, ``git clone`` the repository and install via ``python setup.py install``

 * Install Glue's remaining dependencies by running ``glue-deps install``. For more information on these dependencies see :ref:`below <glue-deps>`.


Dependencies
^^^^^^^^^^^^
.. _glue-deps:

Glue has the following required dependencies:

* Python 2.6, 2.7, or 3.3 and higher
* `Numpy <http://www.numpy.org>`_
* `Matplotlib <http://www.matplotlib.org>`_
* `Pandas <http://pandas.pydata.org/>`_
* Either `PyQt4 <http://www.riverbankcomputing.com/software/pyqt/intro>`_ or `PySide <http://qt-project.org/wiki/PySide>`_

And the following optional dependencies are also highly recommended:

* `SciPy <http://www.scipy.org>`_
* `Astropy <http://www.astropy.org>`_

In addition to these, there are several other optional dependencies to suport
various I/O and other optional functionality. Glue includes a command line
utility ``glue-deps`` to manage dependencies:

* Calling ``glue-deps list`` displays all of Glue's required and optional
  dependencies, along with whether or not each library is already installed on
  your system. For missing dependencies, the program also provides a brief
  description of how it is used within Glue.

* Calling ``glue-deps install`` attempts to ``pip install`` all missing
  libraries. You can install single libraries or categories of libraries by
  providing additional arguments to ``glue-deps install``.

Tips for Ubuntu
^^^^^^^^^^^^^^^

Many dependencies can be reliably installed with ``apt``::

    sudo apt-get install python-numpy
    sudo apt-get install python-scipy
    sudo apt-get install python-matplotlib
    sudo apt-get install python-qt4
    sudo apt-get install pyqt4-dev-tools
    sudo apt-get install ipython
    sudo apt-get install python-zmq
    sudo apt-get install python-pygments


MacPorts
^^^^^^^^
Many dependencies can be reliably installed with::

    sudo port install python27
    sudo port install py27-numpy
    sudo port install py27-scipy
    sudo port install py27-matplotlib
    sudo port install py27-pyqt4
    sudo port install py27-ipython
    sudo port install py27-pip

For information about using MacPorts to manage your Python
installation, see `here
<http://astrofrog.github.com/macports-python/>`_

Running Glue
------------

Installing glue from source will create a executable ``glue`` script
that should be in your path. Running ``glue`` from the command line will
start the program. Glue accepts a variety of command-line
arguments. See ``glue --help`` for examples.

.. note:: On Windows, installation creates an executable ``glue.exe`` file within the python script directory (e.g., ``C:\Python27\Scripts``). Windows users can create a desktop shortcut for this file, and run Glue by double clicking on the icon.

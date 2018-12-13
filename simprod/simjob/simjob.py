#!/usr/bin/python

#!/usr/bin/python
# -*- coding: utf-8 -*-

## Author: Matthieu Marinangeli
## Mail: matthieu.marinangeli@cern.ch
## Description: simulation job class

from .scripts import *
import os
import time
from random import randint, shuffle
from .setup import DoProd
import warnings
import glob
from tqdm import tqdm
from colorama import Fore

from tinydb import JSONStorage, TinyDB, Query
from tinydb.middlewares import CachingMiddleware

simprod = os.getenv("SIMPRODPATH")	
jobsfile = "{0}/simjobs.json".format(simprod)

def getdatabase():
    storage = CachingMiddleware(JSONStorage)
    storage.WRITE_CACHE_SIZE = 1000
    return TinyDB(jobsfile, storage=storage)
    
DATABASE = getdatabase()

DEBUG = 0

class JobCollection(object):
    """
    Simulation job collection.
    """
    
    def __init__(self, **kwargs):
        
        simprod = os.getenv("SIMPRODPATH")+"/simprod"		
        self.jobs = {}
        
        jobs = self.jobcollection

        if len(jobs) > 0:	
                        
            print(red("\nLoading Jobs:"))
            t = tqdm(total=len(jobs))
            
            for k in self.keys:
                
                job_k = self.jobcollection.get(doc_id=k)
                
                if job_k["status"] == "completed":
                    self.jobs[k] = None
                else:
                    self.jobs[k] = SimulationJob.from_doc(job_k)
                    
                t.update(1)
                
            t.close()

        self._update(in_init = True)
        
    @property
    def jobcollection(self):
        return DATABASE.table("jobs")

    @property
    def keys(self):
        return sorted([j.doc_id for j in self.jobcollection.all()], key=int)
        
    def __str__(self):
        
        if DEBUG > 1:
            print("In JobCollection.__str__")
        
        self._update()

        toprint = []		
        toprint.append("{0} jobs".format(len(self.jobs)))
            
        h_job = "    #job "
        h_status = "       status "
        h_evttype = "       evttype "
        h_year = "   year "
        h_nevents = "  #events "
        h_subjobs = "  #subjobs "
            
        header = "|".join([h_job, h_status, h_evttype, h_year, h_nevents, h_subjobs]) + "|"
        line   = "".join(["-" for i in xrange(len(header) - 2)])
                    
        toprint.append(line)
        toprint.append(header)
        toprint.append(line)
            
        for k in self.keys:
            job = self.jobs[k]
                
            if job is not None:
                status  = job.status
                evttype = job.evttype
                year    = job.year
                nevents = job.nevents
                subjobs = job.nsubjobs            
            else:
                job_doc = self.jobcollection.get(doc_id=k)
                status  = job_doc["status"]
                evttype = job_doc["evttype"]
                year    = job_doc["year"]
                nevents = job_doc["nevents"]
                subjobs = job_doc["nsubjobs"]
                    
            if status == "submitted":
                color = cyan
            elif status == "new":
                color = cdefault
            elif status == "submitting":
                color = magenta
            elif status == "running":
                color = green
            elif status == "completed":
                color = blue
            elif status == "failed":
                color = red
                                
            p_job     = "{n:{fill}{al}{w}} ".format(w=(len(h_job)-1), al='>', fill='', n=k)
                        
            p_status  = "{n:{fill}{al}{w}} ".format(w=(len(h_status)-1), al='>', fill='', n=status)
            
            p_evttype = "{n:{fill}{al}{w}} ".format(w=(len(h_evttype)-1), al='>', fill='', n=evttype)
            
            p_year    = "{n:{fill}{al}{w}} ".format(w=(len(h_year)-1), al='>', fill='', n=year)
            
            p_nevents = "{n:{fill}{al}{w}} ".format(w=(len(h_nevents)-1), al='>', fill='', n=nevents)
            
            p_subjobs = "{n:{fill}{al}{w}} ".format(w=(len(h_subjobs)-1), al='>', fill='', n=subjobs)
            
            linejob = "|".join([p_job, p_status, p_evttype, p_year, p_nevents, p_subjobs]) + "|"
                        
            toprint.append(color(linejob))
                
        toprint = "\n".join(toprint)
        
        if DEBUG > 1:
            print("Out of JobCollection.__str__")
                                        
        return toprint
        
    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text('job collection...')
            return
        p.text(self.__str__())
        
    def __geti__(self, i, printlevel = 1):

        if i not in self.keys and i > max(self.keys):
            self._update()
        if i not in self.keys:
            raise ValueError("job {0} not found!".format(i))
        else:
            if self.jobs[i] is None:
                if printlevel > 0:
                    print(green("Loading Job {0}:".format(i)))
                    job_i_doc = self.jobcollection.get(doc_id=i)
                    job_i = SimulationJob.from_doc(job_i_doc)
                    self.jobs[i] = job_i
                
        return self.jobs[i]
                    
    def __getitem__(self, i):
        return self.__geti__(i, printlevel = 1)
                
    def __iter__(self):
        printlevel = -1
        for k in self._keys:
            yield self.__geti__(k, printlevel)		
        
    def __len__(self):
        return len(self.jobcollection)
                
    def select(self, status):
        return self.jobcollection.get(self.query.status == status)
        
    def _update(self, in_init = False):
        
        if DEBUG > 0:
            print("In JobCollection._udpate")
        
        if len(self.jobcollection) > 0:
            condition = (Query().status == "new") | (Query().status == "submitting")
            condition = condition | (Query().status == "submitted")
            to_update = self.jobcollection.search(condition)
        else:
            to_update = []        


        for j in to_update:
            if j.doc_id not in self.jobs.keys():
                self.jobs[j.doc_id] = SimulationJob.from_doc(j)
            elif len(self.jobs[j.doc_id].subjobs) == 0:
                self.jobs[j.doc_id] = SimulationJob.from_doc(j)
            else:
                self.jobs[j.doc_id]._update_job_table(True)
        
        if len(self.jobs) > len(self.keys):
            for k in self.jobs.keys():
                if k not in self.keys:
                    del self.jobs[k]

        for k in self.keys:
            if DEBUG > 0:
                print("In JobCollection._udpate, keys={}".format(k))   
            
            job_doc = self.jobcollection.get(doc_id=k)
            
            if k not in self.jobs.keys():
                job = SimulationJob.from_doc(job_doc)
                self.jobs[k] = job
            else:
                job = self.jobs[k]
            
            if job is None:
                continue
            
            status = job.last_status
            if status != job_doc["status"]:
                _dict = dict(status = status)
                self.jobcollection.update(_dict, doc_ids=[k])

            if status in ["completed", "failed"]:
                self.jobs[k] = None

        if DEBUG > 0:
            print("Out of JobCollection._udpate")

class SimulationJob(object):
    """
    Simulation job
    """
    
    def __init__(self, **kwargs):		
        self.subjobs = {}
        self._options = {}
                    
        self._nevents = kwargs.get('nevents', None)
        if self._nevents is None:
            raise ValueError("Please set nevents!")
        self._neventsjob = kwargs.get('neventsjob', 50)
        self._year = kwargs.get('year', None)
        if self._year is None:
            raise ValueError("Please set year!")
        self._polarities = kwargs.get('polarities', None)
        self._simcond = kwargs.get('simcond', "Sim09e")
        self._stripping = kwargs.get('stripping', None)
        self._turbo = kwargs.get('turbo', False)
        self._mudst = kwargs.get('mudst', False)
        self._runnumber = kwargs.get('runnumber', baserunnumber())
        self._decfiles = kwargs.get('decfiles', 'v30r25')
        self._inscreen = kwargs.get('inscreen', False)
        self._keeplogs = kwargs.get('keeplogs', True)
        self._keepxmls = kwargs.get('keepxmls', True)
        self._redecay = kwargs.get('redecay', False)
        self._status = "new"
        
        self._evttype = kwargs.get('evttype', None)	
        if self._evttype is None:
            raise ValueError("Please set evttype!")
        else:
            self.__setoptfile()
        
        _basedir = os.getenv("SIMOUTPUT")
        if not _basedir:
            _basedir = os.getenv("HOME")+"/SimulationJobs"

        self._options["basedir"] = kwargs.get('basedir', _basedir)
        
        self.deliveryclerk = DeliveryClerk(inscreen=self._inscreen)
        
        if IsSlurm():
            self._options["loginprod"] = True
            
        elif IsLSF():            
            
            if os.getenv("LOG_SIMOUTPUT"):
                self._options["loginprod"] = kwargs.get('loginprod', False)
            else:
                self._options["loginprod"] = kwargs.get('loginprod', True)
                
            if not self._options["loginprod"]:
                self._options["logdir"] = kwargs.get('logdir', os.getenv("LOG_SIMOUTPUT"))
                            
        if not self.options.get("loginprod", True):						
                self._options["logdestdir"]  = "{0}/{1}".format( self.options["logdir"], self.subdir())
                
        self.screensessions = []
        
        self.database = DATABASE
        
        self.jobnumber = None
        
        if kwargs.get("newjob", True):
            jobstable = self.database.table("jobs")
            jobstable.insert(self.outdict())
            self.jobnumber = jobstable._last_id
            if DEBUG > 0:
                print("newjob:", self.jobnumber)
        else:
            self.jobnumber = kwargs.get("jobnumber", None)
            
            
    @property
    def jobtable(self):
        return self.database.table("job_{}".format(self.jobnumber))

    @property
    def range_subjobs(self):
        for n in xrange(self.nsubjobs):
            yield n + 1
                    
    @property
    def nevents( self):
        return self._nevents
        
        
    @nevents.setter
    def nevents( self, value):
        if isinstance(value, (int, float) ):
            self._nevents = int( value )
        else:
            raise TypeError("nevents must be a int!")
            
                
    @property
    def neventsjob( self):
        return self._neventsjob
        
        
    @neventsjob.setter
    def neventsjob( self, value):
        if isinstance(value, (int, float) ):
            self._neventsjob = int( value )
        else:
            raise TypeError("nevents must be a int!")
            
        
    @property
    def nsubjobs(self):
        self._nsubjobs = int( self.nevents/ self.neventsjob )		
        return self._nsubjobs
        
        
    @property
    def evttype(self):
        return self._evttype
        
        
    @evttype.setter
    def evttype(self, value ):
        self._evttype = value		
        self.__setoptfile()
        
        
    @property	
    def simcond(self):
        return self._simcond
        
        
    @simcond.setter	
    def simcond(self, value):
        if not isinstance(value, str):
            raise TypeError("simcond must be a str!")
        if not value in ["Sim09b", "Sim09c"]:
            raise ValueError("simcond must be Sim09b or Sim09c!")
        self._simcond = value
        
        
    @property	
    def stripping(self):
        return self._stripping
        
        
    @stripping.setter	
    def stripping(self, value):
        if not isinstance(value, str):
            raise TypeError("simcond must be a str!")
        if not value in ["21", "24", "28", "24r1", "24r1p1", "28r1", "28r1p1", "29r2"]:
            raise ValueError("stripping must be '21, '24', '28', '24r1', '24r1p1', '28r1', '28r1p1' or '29r2!")
        self._simcond = value
        
        
    @property	
    def year(self):
        return self._year
    
    @year.setter
    def year(self, value):
        if not isinstance(value, int):
            raise TypeError("nevents must be a int!")
        if not value in [2011,2012,2015,2016,2017,2018]:
            raise ValueError("year must be 2011, 2012, 2015, 2016, 2017 or 2018!")
        self._year = value
        
    @property
    def keys(self):
        return self.subjobs.keys()
        
    @property	
    def options(self):
        return self._options
        
    def subdir(self):
        subdir = "simProd_{0}_{1}".format(self.evttype, self.simcond)
        if self.turbo:
            subdir += "_Turbo"
        if self.mudst:
            subdir += "_muDST"
        if self.redecay: 
            subdir += "_ReDecay"
        
        self.options["subdir"] = subdir
        
        return subdir
        
    
    @property	
    def proddir(self):
        self._proddir  = "{0}/{1}".format(self.options["basedir"], self.subdir())
        return self._proddir
        
        
    @property	
    def destdir(self):
        self._destdir = "{0}/{1}/{2}/{3}".format(self.options["basedir"], 
                                                 self.evttype, 
                                                 self.year, 
                                                 self.simcond)
        if self._redecay:
            self._destdir += "_ReDecay"
        return self._destdir
        
    
    @property	
    def optfile(self):
        return self._optfile
        
        
    @property	
    def turbo(self):
        return self._turbo
        
        
    @turbo.setter	
    def turbo(self, value):
        if isinstance(value, bool):
            self._turbo = value
        else:
            raise TypeError("turbo must be set to True/False!")
            
    
    @property	
    def mudst(self):
        return self._mudst
        
        
    @mudst.setter	
    def mudst(self, value):
        if isinstance(value, bool):
            self._mudst = value
        else:
            raise TypeError("mudst must be set to True/False!")
            
            
    @property
    def keeplogs(self):
        return self._keeplogs
        
        
    @keeplogs.setter	
    def keeplogs(self, value):
        if isinstance(value, bool):
            self._keeplogs = value			
        else:
            raise TypeError("keeplogs must be set to True/False!")
            
            
    @property
    def keepxmls(self):
        return self._keepxmls
        
        
    @keepxmls.setter	
    def keepxmls(self, value):
        if isinstance(value, bool):
            self._keepxmls = value			
        else:
            raise TypeError("keepxmls must be set to True/False!")
            
            
    @property
    def redecay(self):
        return self._redecay
        
        
    @redecay.setter	
    def redecay(self, value):
        if isinstance(value, bool):
            self._redecay = value
        else:
            raise TypeError("redecay must be set to True/False!")
            

    def getrunnumber(self, job_number = None ):
        if job_number != None and not isinstance(job_number, int):
            raise TypeError("Job number must be a 'int'. Got a '{0}' instead!".format(job_number.__class__.__name__))
        
        if job_number == None:
            return self._runnumber
        else:
            return self._runnumber + job_number
            
            
    def prepare( self, update_table=True, **kwargs ):
        if len(self.subjobs) < 1:
                    
            if not self._evttype:
                raise ValueError('Evttype not defined!')
                
            if not self._nevents:
                raise ValueError('nevents not defined!')
                
            if not self._neventsjob:
                raise ValueError('neventsjob not defined!')
                
            if not self._year:
                raise ValueError('year not defined!')
                
            if not self._simcond:
                raise ValueError('simcond not defined!')
                
            checksiminputs(self)
            
            if  self.nsubjobs  == 0:
            
                self.neventsjob = int(self.nevents / 2)
                self.nevents    = self.neventsjob * 2
        
            def sample_polarities():
                polarities = ["MagUp", "MagDown"]
                i = randint(0, 1)
                p1 = polarities.pop(i)
                p2 = polarities[0]
                
                polarity = [p1 for i in xrange(1, int(self.nsubjobs / 2) + 1)]
                polarity += [p2 for i in xrange(int(self.nsubjobs / 2) + 1, self.nsubjobs + 1)]
                return shuffle(polarity)
                        
            if not isinstance(self._polarities, list):
                if self._polarities is None:
                    self._polarities = sample_polarities()
                elif self._polarities in ["MagUp", "MagDown"]:
                    self._polarities = [self._polarities for i in self.range_subjobs]
                else:
                    raise ValueError()
            else:
                if len(self._polarities) != self.nsubjobs:
                    self._polarities = sample_polarities()
                elif not all(p in ["MagUp", "MagDown"] for p in self._polarities):
                    raise ValueError()
                                                                        
        infiles = kwargs.get('infiles', [])
                
        for n in self.range_subjobs:				
            if self.subjobs.get(n, None) is not None:
                continue
                
            self._preparesubjobs(n, infiles=infiles)
            
        if update_table:
            self._update_job_table(update_subjobs=True)
        
                            
    def _preparesubjobs( self, sjn, **kwargs ):
        
        if DEBUG > 2:
            print(sjn)
                        
        if self._polarities:	
            polarity  = self._polarities[sjn-1]
        else:
            if sjn <= int(self.nsubjobs/2):
                polarity = "MagUp"
            else:
                polarity = "MagDown"
                
        if sjn not in self.keys:
            runnumber = self.getrunnumber(sjn)
            self.subjobs[sjn] = SimulationSubJob( parent=self, polarity=polarity, runnumber=runnumber, subjobnumber=sjn, **kwargs )	
        

    def send( self, job_number = None ):
        
        if self.status == "completed":
            print("Job is completed. There is nothing to send.")
        else:
            failedsubjobs = self.select("failed")
                    
            if len(failedsubjobs) > 0:
                for sj in failedsubjobs:
                    sj.reset()
            self.deliveryclerk.send_job(self)
            self._update_job_table(True)            
            
        
        
    def cancelpreparation( self, **kwargs ):	
        for n in self.range_subjobs:				
            if self.subjobs.get(n, None):
                del self.subjobs[n]
        self.jobtable.purge()
        
        
    def remove( self ):
        if self.jobnumber:
            info_msg = "INFO\tremoving job {0}".format(self.jobnumber)
        else:
            info_msg = "INFO\tremoving job"
        print(info_msg)
                
        for n in self.range_subjobs:
            sj = self[n]
            
            if sj and sj.status == "running":
                sj.kill(storeparent = False)
            
        self.database.purge_table("job_{}".format(self.jobnumber))
        self.database.table("jobs").remove(doc_ids=[self.jobnumber])
        self.deliveryclerk.kill()
        
    
    def __getitem__(self, sjob_number):
        
        if DEBUG > 0:
            msg = "in SimulationJob.__getitem__, jobnumber:{0}, sjobnumber={1}"
            print(msg.format(self.jobnumber, sjob_number))

        if not isinstance(sjob_number, int):
            msg = "Job number must be a 'int'. Got a '{0}' instead!"
            raise TypeError(msg.format(sjob_number.__class__.__name__))
            
        if not sjob_number in self.keys:
            print("WARNING\tsubjob {0}.{1} has been lost!".format(self.jobnumber, sjob_number))
            self.subjobs[sjob_number] = self._load_subjob(sjob_number, force_load = True)
                            
        subjob = self.subjobs[sjob_number]
        
        if subjob is None:
            self.subjobs[sjob_number] = self._load_subjob(sjob_number, force_load = True)

        return self.subjobs[sjob_number]
        
        
    def __setitem__(self, sjob_number, subjob):
        
        if not isinstance(sjob_number, int):
            msg = "Job number must be a 'int'. Got a '{0}' instead!"
            raise TypeError(msg.format(sjob_number.__class__.__name__))
        
        if subjob:
            if not isinstance(subjob, SimulationSubJob):
                msg = "Must receive a SimulationSubJob. Got a '{0}' instead!"
                raise TypeError(msg.format(subjob.__class__.__name__))
            
        self.subjobs[sjob_number] = subjob
        
        
    def __iter__(self):
        for n in self.range_subjobs:
            yield self[n]
            
        
    def select(self, status):
        return [self[n] for n in self.range_subjobs if self[n].status == status]
                
    @property
    def last_status( self):	
        return self._status
        
    @property
    def status( self):
        
        if DEBUG > 0:
            print("in SimulationJob.status, jobnumber:{0}".format(self.jobnumber))

        if not(self.last_status == "completed"):
            
            nsubmitted = 0
            nrunning   = 0
            ncompleted = 0
            nfailed    = 0
            
            keys = self.keys
                                                            
            for n in self.range_subjobs:
                
                if n in keys:
                    sj_doc = self.jobtable.get(doc_id=n)
                    subjob = self.subjobs[n]
                
                    if subjob is None:
                        status = sj_doc["status"]
                    else:
                        status = subjob.status
                        jobid  = subjob.jobid
                        
                        _dict = {}
                        
                        if sj_doc["jobid"] != jobid:
                            _dict["jobid"] = jobid
                        if sj_doc["status"] != status:
                            _dict["status"] = status
                            
                        if len(_dict) > 0:
                            self.jobtable.update(_dict, doc_ids=[n])
                        
                        if status in ["completed", "failed"]:
                            self[n] = None
                        
                else:
                    status = "new"
                                
                if status == "submitted":
                    nsubmitted += 1
                elif status == "running":
                    nrunning   += 1
                    nsubmitted += 1
                elif status == "completed":
                    ncompleted += 1
                    nsubmitted += 1
                elif status == "failed":
                    nfailed    += 1
                    nsubmitted += 1
                                        
            if nsubmitted == 0:
                _status = "new"	
            elif nsubmitted < self.nsubjobs and nsubmitted > 0:
                _status = "submitting"
            elif nsubmitted == self.nsubjobs and nrunning == 0 and nfailed == 0 and ncompleted < self.nsubjobs:
                _status = "submitted"
            elif nsubmitted == self.nsubjobs and nrunning > 0:
                _status = "running"
            elif nsubmitted == self.nsubjobs and nrunning == 0 and ncompleted == self.nsubjobs and nfailed == 0:
                _status = "completed"
            elif nsubmitted == self.nsubjobs and nrunning == 0 and ncompleted < self.nsubjobs and nfailed > 0:
                _status = "failed"
                
            if _status == "completed":
                self.deliveryclerk.clear(self)
                                
            if _status != self._status:
                info_msg = "INFO\tstatus of job {0} changed from '{1}' to '{2}'"
                info_msg = info_msg.format(self.jobnumber, self._status, _status)

                print(info_msg)
                self._status = _status
                self._update_job_table(True)

                
            self._status = _status
            
        if DEBUG > 0:
            print("Out of SimulationJob.status, jobnumber:{0}".format(self.jobnumber))
            
        return self._status
        
    def __setoptfile( self ):
        moddir = os.getenv("SIMPRODPATH")
        self._optfile = "{0}/EvtTypes/{1}/{1}.py".format( moddir, self._evttype )
    
        if not os.path.isfile( self._optfile ):
            getevttype( evttype = self._evttype, decfiles = self._decfiles )
            
                    
    def outdict(self):

        status = self.last_status
                
        outdict = {"evttype": self.evttype,
                   "year" : self.year,
                   "nevents": self.nevents,
                   "neventsjob": self.neventsjob,
                   "nsubjobs": self.nsubjobs,
                   "runnumber": self._runnumber,
                   "simcond": self.simcond,
                   "polarities": self._polarities,
                   "stripping": self.stripping,
                   "mudst": self.mudst,
                   "turbo": self.turbo,
                   "basedir": self.options["basedir"],
                   "proddir" : self.proddir,
                   "destdir": self.destdir,
                   "subdir": self.options["subdir"],
                   "loginprod": self.options["loginprod"],    
                   "screensessions": self.screensessions,
                   "status": status,
                   "keeplogs": self._keeplogs,
                   "keepxmls": self._keepxmls,
                   "redecay": self._redecay,
                   "deliveryclerk": self.deliveryclerk.outdict()
                   } 
            
        if not self.options["loginprod"]:
            outdict["logdir"]     = self.options["logdir"]
            outdict["logdestdir"] = self.options["logdestdir"]
            
        return outdict
        
            
    def _update_job_table(self, update_subjobs = False):
        
        if DEBUG > 0:
            print("in SimulationJob._update_job_table, jobnumber:{0}".format(self.jobnumber))
                
        jobstable = self.database.table("jobs")

        jobstable.update(self.outdict(), doc_ids=[self.jobnumber])
        
        if update_subjobs:
            if DEBUG > 0:
                print("in SimulationJob._update_job_table, update subjobs")
            table = self.deliveryclerk.get_update_subjobs(self)
                                
            for n in self.range_subjobs:
                
                job = self[n]
                
                if job.status  == "completed":
                    continue
                    
                else:
                    if table is not None:
                        doc = table.get(Query().subjobnumber == n)
                        if DEBUG > 0:
                            print(n, doc)
                    else:
                        doc = None
                    
                    if doc is not None:
                        if DEBUG > 0:
                            print(n, doc["runnumber"], self.getrunnumber(n))
                        assert doc["runnumber"] == self.getrunnumber(n)
                        _dict = {}
                        
                        if doc["jobid"] != job.jobid:
                            job.jobid = doc["jobid"]
                        if doc["status"] != job.status and job.status == "new":
                            job._status = doc["status"]
                            
                        if doc["status"] != "new" and doc["jobid"] is not None:
                            job._submitted = True
                            
                    else:
                        job._update_subjob_table()
 
        if DEBUG > 0:
            print("Out of SimulationJob._update_job_table, jobnumber:{0}".format(self.jobnumber))
                        
    @classmethod
    def from_dict(cls, dict, jobnumber, inscreen = False, printlevel = 1):
        
        if DEBUG > 0:
            print("in SimulationJob.from_dict")
                
        simjob = cls( 
                    evttype=dict["evttype"],
                    year=dict["year"],
                    nevents=dict["nevents"],
                    neventsjob=dict["neventsjob"],
                    runnumber=dict["runnumber"],
                    polarities=dict.get("polarities", None),
                    simcond=dict["simcond"],
                    stripping=dict["stripping"],
                    mudst=dict["mudst"],
                    turbo=dict["turbo"],	
                    basedir=dict["basedir"],
                    newjob=False,
                    jobnumber=jobnumber
                    )						

        simjob.jobnumber = jobnumber	
        simjob._options["subdir"] = dict["subdir"]
        simjob._options["loginprod"] = dict["loginprod"]
        simjob.screensessions = dict["screensessions"]
        simjob._status = dict.get("status", "new")
        simjob._keeplogs = dict.get("keeplogs", True)
        simjob._keepxmls = dict.get("keepxmls", True)
        simjob._redecay = dict.get("redecay", False)
        
                
        if not simjob._options["loginprod"]:
            simjob._options["logdir"] = dict["logdir"]
            simjob._options["logdestdir"] = dict["logdestdir"]
            
        simjob._options["cpumemory"] = dict.get("cpumemory", None)
        if not simjob._options["cpumemory"]:
            simjob._options["cpumemory"] = dict.get("cpu", None)
                
        simjob.deliveryclerk = DeliveryClerk.from_dict(dict["deliveryclerk"])
                    
        if DEBUG > 0:
            print(simjob.jobtable)
            
        if len(simjob.jobtable) > 0:
            
            if printlevel > 0:
                t = tqdm(total=simjob.nsubjobs, 
                        bar_format="{l_bar}%s{bar}%s{r_bar}" % (Fore.BLUE, Fore.RESET), 
                        desc=cyan("\tLoading subjobs"))
            else:
                t = None
            
            simjob.subjobs = {n:simjob._load_subjob(n, t, printlevel) for n in simjob.range_subjobs}
                                                                
            if printlevel > 0:																		
                t.close()
                            
    #        if to_store:
    #            simjob._update_job_table(False)
                
        return simjob
            
    @classmethod
    def from_doc(cls, doc, inscreen = False, printlevel = 1):
        
        if DEBUG > 0:
            print("in SimulationJob.from_doc")

        jobnumber = doc.doc_id
        simjob = cls.from_dict(doc, jobnumber, inscreen, printlevel)
                
        return simjob
        
    def _load_subjob( self, nsj, pbar = None, printlevel = 0, force_load = False ):
                
        sj_doc = self.jobtable.get(doc_id=nsj)
        status = sj_doc["status"]
        
        if status in ["completed", "failed"] and not force_load:
            sj = None
        else:
            sj = SimulationSubJob.from_doc( self, sj_doc)
            
        if printlevel > 0:			
            pbar.update(1)
                            
        return sj
            
    def __str__(self):
            
        if len(self.subjobs) > 0:
            
            toprint = []
            
            toprint.append("evttype: {0}; year: {1}; #events {2}; stripping {3}; simcond {4}; {5} jobs".format( 
                        self.evttype,
                        self.year,
                        self.nevents,
                        self.stripping,
                        self.simcond,
                        self.nsubjobs ))
            
            h_job        = "    #job "
            h_jobID      = "    job ID "
            h_status     = "       status "
            h_runnumber  = "      runnumber "
            h_polarity   = "   polarity "
            h_nevents    = "  #events "
            
            header = [h_job, h_jobID, h_status, h_runnumber, h_polarity, h_nevents]
            header = "|".join(header) + "|"	
            line   = "".join(["-" for i in xrange(len(header) - 2)])
                    
            toprint.append(line)
            toprint.append(header)
            toprint.append(line)

            for n in self.range_subjobs:
                
                sj_doc = self.jobtable.get(doc_id=n)
                
                if self.subjobs[n] is None:
                    status    = sj_doc["status"] 
                    jobID     = sj_doc["jobid"]
                    runnumber = self.getrunnumber(n)
                    polarity  = sj_doc["polarity"]
                else:				
                    job = self[n]				
                    status    = job.status
                    jobID     = job.jobid
                    runnumber = job.runnumber
                    polarity  = job.polarity
                    
                    _dict = {}
                    
                    if sj_doc["jobid"] != job.jobid:
                        _dict["jobid"] = job.jobid
                    if sj_doc["status"] != job.status:
                        _dict["status"] = job.status
                        
                    if len(_dict) > 0:
                        self.jobtable.update( _dict, doc_ids=[n])
                        
                nevents   = self.neventsjob
                
                if status == "submitted":
                    color = cyan
                elif status == "new":
                    color = cdefault
                elif status == "running":
                    color = green
                elif status == "completed":
                    color = blue
                elif status == "failed":
                    color = red
                        
                p_job       = "{n:{fill}{al}{w}} ".format(w=(len(h_job)-1), al='>', fill='', n=n)
                
                p_jobID     = "{n:{fill}{al}{w}} ".format(w=(len(h_jobID)-1), al='>', fill='', n=jobID)
                
                p_status    = "{n:{fill}{al}{w}} ".format(w=(len(h_status)-1), al='>', fill='', n=status)
                
                p_runnumber = "{n:{fill}{al}{w}} ".format(w=(len(h_runnumber)-1), al='>', fill='', n=runnumber)
                
                p_polarity  = "{n:{fill}{al}{w}} ".format(w=(len(h_polarity)-1), al='>', fill='', n=polarity)
                
                p_nevents   = "{n:{fill}{al}{w}} ".format(w=(len(h_nevents)-1), al='>', fill='', n=nevents)
                
                linejob = "|".join([p_job, p_jobID, p_status, p_runnumber, p_polarity, p_nevents]) + "|"
                
                toprint.append(color(linejob))
                
            toprint = "\n".join(toprint)
            
            
                                    
        else:
            toprint = self.__repr__()
        
        return toprint
        
            
    def _repr_pretty_(self, p, cycle):
        if cycle:
            p.text('simulation job...')
            return
        p.text(self.__str__())   
                 

                    
class SimulationSubJob(object):
    """
    Simulation subjob.
    """
    
    def __init__(self, parent, polarity, runnumber, subjobnumber, **kwargs):
        self.parent = parent
        self.polarity = polarity
        self.runnumber = runnumber
        self.subjobnumber = subjobnumber
        self.jobid = None
        self.send_options = self.parent.options.copy()
        self._status = "new"
                        
        self._infiles = kwargs.get("infiles", [])
        self.send_options["infiles"] = self._infiles
        self.keeplog = self.parent.keeplogs
        self.keepxml = self.parent.keepxmls
        
        self.jobname = "{0}_{1}_{2}evts_s{3}_{4}".format(self.parent.year, 
                                                         self.polarity, 
                                                         self.parent.neventsjob, 
                                                         self.parent.stripping, 
                                                         self.runnumber)
                                                        
        self.jobdir = "{0}/{1}".format(self.parent.proddir, self.jobname)
        
        ext = "dst"	
        if self.parent.mudst:
            ext = "mdst"
            
        self.prodfile = "{0}/{1}_events.{2}".format(self.jobdir, self.parent.neventsjob, 
                                                    ext)
                                                        
        self.destfile = "{0}/{1}/{2}evts_s{3}_{4}.{5}".format(self.parent.destdir, 
                                                              self.polarity, 
                                                              self.parent.neventsjob, 
                                                              self.parent.stripping, 
                                                              self.runnumber, 
                                                              ext)
                                                                                    
        if not self.send_options["loginprod"]:
            self.logjobdir = "{0}/{1}".format(self.send_options["logdestdir"],
                                              self.jobname)
            
        
        self.send_options["jobname"] = self.jobname
        self.send_options["infiles"] = self.infiles
        self.send_options["command"] = self._command()
        
        self._submitted = False
        self._running   = False
        self._finished  = False
        self._completed = False
        self._failed    = False
        
        if kwargs.get("newsubjob", True):
            self.parenttable.insert(self.outdict())
            assert self.parenttable._last_id == subjobnumber
        
        if kwargs.get("to_store", False):
            self._update_subjob_table()
            
            
    @property
    def parenttable(self):
        return self.parent.jobtable
        
        
    @property
    def infiles(self):
        return self._infiles
        
    @infiles.setter
    def infiles(self, files):
        if not isinstance(files, (list, tuple)):
            raise TypeError("A list/tuple with infiles must me provided.")
            
        if not all(isinstance(f, str) for f in files):
            raise TypeError("Infiles must be str.")
            
        self._infiles = files
        self.send_options["infiles"] = files
                                
                                    
    def send(self):
        
        if not self._submitted:
        
            self.jobid = self.parent.deliveryclerk.send_subjob(self)
            
            if self.jobid:
                self._submitted = True
                self._running   = False
                self._finished  = False
                self._completed = False
                self._failed    = False
                self._status    = "submitted"
                            
                time.sleep(0.07)
                print(blue("{0}/{1} jobs submitted!".format(int(self.subjobnumber), self.parent.nsubjobs)))
                time.sleep(0.07)				
            else:
                print(red("job {0}/{1} submission failed, try later!".format(int(self.subjobnumber), self.parent.nsubjobs)))
                    
            self._update_subjob_table()
                    

    @property
    def last_status(self):
        return self._status
                    
    @property
    def status(self):
        
        _previous = self.last_status
                
        if not(_previous == "failed" or _previous == "completed"):
            
            if not self._finished and self._submitted:
                self._updatestatus()
            if not self._submitted:
                self._status = "new"
            elif self._submitted and not self._running and not self._finished:
                self._status = "submitted"
            elif self._submitted and self._running and not self._finished:
                self._status = "running"
            elif self._submitted and not self._running and self._finished:
                if self._completed:
                    self._status = "completed"
                    if not self.output == self.destfile and not self.output == "":
                        self._move_jobs()
                elif self._failed:
                    self._status = "failed"
                    self._empty_proddir(keep_log = True)
                    
            
                    
            if _previous != self._status:
                
                if self.parent.jobnumber:
                    info_msg = "INFO\tstatus of subjob {0}.{1} changed from '{2}' to '{3}'"
                    info_msg = info_msg.format(self.parent.jobnumber, self.subjobnumber,
                                               _previous, self._status)
                else:
                    info_msg = "INFO\tstatus of job (evttype {0}, year {1}, run number {2})"
                    info_msg += " changed from '{3}' to '{4}'."
                    info_msg = info_msg.format(self.parent.evttype, self.parent.year,
                                               self.runnumber, _previous, self._status)
                                                                                                                                                                    
                print(info_msg)	
                self._update_subjob_table()
                
        return self._status
        
    def _updatestatus(self):
        
        status = GetStatus(self.jobid)	
                        
        if status == "running":
            self._running = True
            
        elif status == "completed" or status == "cancelled" or status == "failed" or status == "notfound":
            self._running = False
            self._finished = True
                        
            if self.output != "" and os.path.isfile(self.output):							
                if os.path.isfile(self.output) and os.path.getsize(self.output) > 900000:
                    self._completed = True
                elif os.path.isfile(self.output) and os.path.getsize(self.output) < 900000:
                    self._failed = True	
            elif self.output == "":
                self._failed = True
                                        
    @property
    def output(self):
        if os.path.isfile(self.prodfile):
            return self.prodfile
        elif os.path.isfile(self.destfile):
            return self.destfile	
        else:
            return ""
            
    def reset(self):
        
        if self._status == "completed":
            self.kill()
            
        self._empty_proddir()
        self.jobid = None
        self._submitted = False
        self._running = False
        self._finished = False
        self._completed = False
        self._failed = False
        self._status = "new"
        self._update_subjob_table()
            
    def _command(self):
        doprod = DoProd(self.parent.simcond, self.parent.year)
        
        command = doprod
        command += ' {0}'.format(self.parent.optfile)
        command += ' {0}'.format(self.parent.neventsjob)
        command += ' {0}'.format(self.polarity)
        command += ' {0}'.format(self.runnumber)
        command += ' {0}'.format(self.parent.turbo)
        command += ' {0}'.format(self.parent.mudst)
        command += ' {0}'.format(self.parent.stripping)
        command += ' {0}'.format(self.parent.redecay)
            
        return command
                                    
    def kill(self, storeparent=True):
        
        if self.parent.jobnumber:
            info_msg = "INFO\tkilling subjob {0}.{1}"
            info_msg = info_msg.format(self.parent.jobnumber,
                                       self.subjobnumber)
        else:
            info_msg = "INFO\tkilling subjob {0}".format(self.subjobnumber)
        
        print(info_msg)
        
        if self._submitted:
            Kill( self.jobid )
                
        self._failed = True
        self._running = False
        self._completed = False
        self._finished  = True
        self._status    = "failed"
        self._update_subjob_table()
        if storeparent:
            self.parent._store_job_table()
        self._empty_proddir()
            
    def _empty_proddir(self, keep_log=False):
        if os.path.isdir(self.jobdir):
            if keep_log and self.send_options["loginprod"]:
                files = glob.iglob(self.jobdir + "/*")
                for f in files:
                    if "out" in f:
                        continue
                    elif "err" in f:
                        continue
                    else:
                        os.remove(f) 
            else:
                silentrm(self.jobdir)
                
        if not self.send_options["loginprod"] and not keep_log:
            if os.path.isdir(self.logjobdir):
                silentrm(self.logjobdir)
                
    def _move_jobs(self):
        
        if not os.path.isdir(self.jobdir):
            msg = " WARNING: production folder has been removed, if the jobs is marked as"
            msg += "failed the output hasbeen probably lost!"
            warnings.warn(red(msg), stacklevel=2)
            
        else:
            dst_prodfile = self.prodfile

            if "eos" in dst_prodfile:
                mover = EosMove
            else:
                mover = Move
                    
            xml_prodfile = os.path.dirname(dst_prodfile) + "/GeneratorLog.xml"
            dst_destfile = self.destfile
            xml_destfile = os.path.dirname(self.destfile) + "/xml/{0}.xml".format(self.runnumber)
            
            
            if self.parent.jobnumber:
                info_msg = "INFO\tMoving subjob {0}.{1} to final destination!"
                info_msg = info_msg.format(self.parent.jobnumber,
                                           self.subjobnumber)
            else:
                info_msg = "INFO\tMoving subjob (evttype {0}, year {1}, run number {2}) to final destination!"
                info_msg = info_msg.format(self.parent.evttype,
                                           self.parent.year,
                                           self.runnumber)
                    
            print(info_msg)
            
            if os.path.isfile(dst_prodfile):
                mover(dst_prodfile, dst_destfile)
            else:
                warn_msg = red("WARNING\tdst output is not found. It has probably been moved or erased manually")
                print(warn_msg)
                
            if self.keepxml:		
                if os.path.isfile(xml_prodfile):
                    mover(xml_prodfile, xml_destfile)
                else:
                    warn_msg = red("WARNING\tGeneratorLog.xml is not found. It has probably been moved or erased manually")
                    print(warn_msg)
                
            self._empty_proddir(self.keeplog)
           
         
    def outdict(self):
        
        outdict = {
               "runnumber": self.runnumber,
               "polarity": self.polarity,
               "jobid": self.jobid,
               "status": self._status,
               "infiles": self.infiles
               }
            
        if not self.send_options["loginprod"]:
            outdict["logjobdir"] = self.logjobdir
            
        return outdict
                    
    def _update_subjob_table(self):
        
        self.parenttable.update(self.outdict(), Query().runnumber == self.runnumber)
                          

    @classmethod
    def from_dict(cls, parent, dict, subjobnumber, to_store=True):
        
        simsubjob = cls( 
                        parent    = parent, 
                        polarity  = dict["polarity"],
                        runnumber = dict["runnumber"],
                        subjobnumber = subjobnumber,
                        newsubjob = False 
                        )
                        
        simsubjob.jobid = dict["jobid"]
        simsubjob.infiles = dict.get("infiles",[])
        simsubjob.send_options["infiles"] = dict.get("infiles",[])
        
        status = dict["status"]
        simsubjob._status = dict["status"]
        
        if status == "submitted":
            simsubjob._submitted = True
        elif status == "running":
            simsubjob._submitted = True
            simsubjob._running   = True
        elif status == "failed":
            simsubjob._submitted = True
            simsubjob._finished  = True
            simsubjob._failed    = True
        elif status == "completed":
            simsubjob._submitted = True
            simsubjob._finished  = True
            simsubjob._completed = True
                            
        if not simsubjob.send_options["loginprod"]:
            simsubjob.logjobdir = dict["logjobdir"]
            
        if to_store:
            simsubjob._update_subjob_table()
        
        return simsubjob
    
    
    @classmethod
    def from_doc(cls, parent, doc, to_store = True ):
        
        subjobnumber = doc.doc_id
        simsubjob = cls.from_dict(parent, doc, subjobnumber, to_store)
                
        return simsubjob
        
        
# utilities

def checksiminputs(job):
    
    def StrippingVersion(*args):
        args = list(args)
        with warnings.catch_warnings():
            warnings.simplefilter("always")	
            if job._stripping == None:
                job._stripping = args[0]
                if len(args) > 1:
                    warnings.warn( red("Default stripping version {0} used. {1} versions are available.".format( 
                                    job._stripping, 
                                   	args)), 
                                   	stacklevel = 2)
            elif job._stripping not in args:
                raise NotImplementedError( "Stripping version {0} is not available for {1} {2}! Only {3}!".format( 
                                   	job._stripping, 
                                   	job._year, 
                                   	job._simcond, 
                                   	args) )	
                    
    if job._simcond == "Sim09b" and job._year in [2011, 2017, 2018]:
        raise NotImplementedError( "{0} setup is not (yet) implemented for {1}!".format(
                                    job._year, 
                                    job._simcond) )
        
    elif job._simcond == "Sim09c" and job._year in [2017, 2018]:
        raise NotImplementedError( "{0} setup is not (yet) implemented for {1}!".format(
                                    job._year, 
                                    job._simcond) )
        
    elif job._simcond == "Sim09d" and job._year in [2011, 2012, 2015, 2016, 2017, 2018]:
        raise NotImplementedError( "{0} setup is not (yet) implemented for {1}!".format(
                                    job._year, 
                                    job._simcond) )
                                    
    elif job._simcond == "Sim09e" and job._year in [2011, 2012, 2018]:
        raise NotImplementedError( "{0} setup is not (yet) implemented for {1}!".format(
                                    job._year, 
                                    job._simcond) )									
    
                                    
    if job._year == 2011:
        if job._simcond == "Sim09c":
            StrippingVersion("21r1")
    
    if job._year == 2012:
        if job._simcond == "Sim09b":
            StrippingVersion("21")
        elif job._simcond == "Sim09c":
            StrippingVersion("21")
        
    elif job._year == 2015:
        if job._simcond == "Sim09b":
            StrippingVersion("24")
        if job._simcond in ["Sim09c", "Sim09e"]:
            StrippingVersion("24r1", "24r1p1")
        
    elif job._year == 2016:
        if job._simcond == "Sim09b":
            StrippingVersion("28")
        if job._simcond in ["Sim09c", "Sim09e"]:
            StrippingVersion("28r1", "28r1p1")	
            
    elif job._year == 2017:
        StrippingVersion("29r2")
                            
    if job._mudst and ( job._year == 2012 or job._year == 2011 ):
        raise NotImplementedError( "No micro DST output for {0}!".format(job._year) )
            
    if job._turbo and ( job._year == 2012 or job._year == 2011 ):
        raise NotImplementedError( "Turbo is not implemented for {0}!".format(job._year) )



            
                        

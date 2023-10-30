""" Executor to set status "Scouting" for a main job which has scout jobs
"""

from DIRAC import S_OK, S_ERROR

from DIRAC.WorkloadManagementSystem.Executor.Base.OptimizerExecutor import OptimizerExecutor
from DIRAC.WorkloadManagementSystem.Client import JobStatus
from DIRAC.ResourceStatusSystem.Client.SiteStatus import SiteStatus
from DIRAC.WorkloadManagementSystem.Client.JobStateUpdateClient import JobStateUpdateClient


class Scouting(OptimizerExecutor):
    """
      The specific Optimizer must provide the following methods:
      - optimizeJob() - the main method called for each job
      and it can provide:
      - initializeOptimizer() before each execution cycle
    """

    @classmethod
    def initializeOptimizer(cls):
        """ Initialization of the optimizer.
        """
        cls.__jobDB = JobStateUpdateClient()
        return S_OK()

    def optimizeJob(self, jid, jobState):
        self.jobLog.info('Getting scoutparams from JobParameters')

        result = self.__jobDB.getJobParameters(jid, ['ScoutFlag', 'ScoutID'])
        if not result['OK']:
            return result

        rCounter = 0
        if result['Value']:
            scoutparams = result['Value'].get(jid)
            self.jobLog.info('scoutparams: %s' % scoutparams)
            if not scoutparams:
                self.jobLog.info('Skipping optimizer, since scoutparams are abnormal')
                return self.setNextOptimizer(jobState)

            scoutID, scoutFlag = self.__getIDandFlag(scoutparams)
            if not scoutID:
                self.jobLog.info('Skipping optimizers, since this job has not enough scoutparams.')
                return self.setNextOptimizer(jobState)

        else:
            result = jobState.getManifest()
            if not result['OK']:
                return result
            jobManifest = result['Value']
            scoutID = jobManifest.getOption('ScoutID', None)
            if not scoutID:
                self.jobLog.info('Skipping optimizer, since no scout \
                                 corresponding to this job group')
                return self.setNextOptimizer(jobState)

            scoutFlag = 0
            result = jobState.getAttribute('RescheduleCounter')
            if not result['OK']:
                return S_ERROR('Could not retrieve RescheduleCounter')
            if result['Value'] == None:
                return S_ERROR('Reschedule Counter not found')

            rCounter = result['Value']
            if int(rCounter) > 0:
                rCycle = int(rCounter) - 1
                result = self.__jobDB.getAtticJobParameters(jid, ['"ScoutFlag"'],
                                                    rescheduleCounter=rCycle)
                self.jobLog.info("From AtticJobParameter: %s" % result)
                if result['OK']:
                    try:
                        scoutFlag = result['Value'].get(rCycle).get('ScoutFlag', 0)
                    except:
                        pass
                else:
                    self.jobLog.info(result['Message'])
            self.jobLog.info('Setting scoutparams (ID:%s, Flag:%s) to JobParamter'
                              % (scoutID, scoutFlag))
            result = self.__setScoutparamsInJobParameters(jid, scoutID, scoutFlag, jobState)
            if not result['OK']:
                self.jobLog.info('Skipping, since failed in setting scoutparams of JobParameters.')
                return self.setNextOptimizer(jobState)

        if int(scoutFlag) == 1:
            self.jobLog.info('Skipping optimizer, since corresponding scout jobs complete \
                             (ScoutFlag = %s)'% scoutFlag)
            return self.setNextOptimizer(jobState)

        self.jobLog.info('Job %s set scouting status' % jid)
        return self.__setScoutingStatus(jobState)

    def __getIDandFlag(self, scoutparams):

        scoutID = scoutparams.get('ScoutID')
        scoutFlag = scoutparams.get('ScoutFlag')
        return scoutID, scoutFlag

    def __setScoutparamsInJobParameters(self, jid, scoutID, scoutFlag, jobState=None):

        if not jobState:
            jobState = self.__jobData.jobState

        paramList = []
        paramList.append(('ScoutID', scoutID))
        paramList.append(('ScoutFlag', scoutFlag))
        result = self.__jobDB.setJobParameters(jid, paramList)
        if not result['OK']:
            self.jobLog.info('Skipping, since failed in recovering scoutparams of JobParameters.')
            
        return result

    def __setScoutingStatus(self, jobState=None):

        if not jobState:
            jobState = self.__jobData.jobState

        result = jobState.getStatus()
        if not (result := jobState.getStatus())['OK']:
            return result

        opName = self.ex_optimizerName()
        result = jobState.setStatus(self.ex_getOption('WaitingStatus', JobStatus.SCOUTING),
                                    minorStatus=self.ex_getOption('WaitingMinorStatus',
                                                                  'Waiting for Scout Job Completion'),
                                    appStatus="Unknown",
                                    source=opName)
        if not result['OK']:
            return result
        
        return S_OK()
    
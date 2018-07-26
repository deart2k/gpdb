#!/usr/bin/env python
#
# Copyright (c) Greenplum Inc 2008. All Rights Reserved. 
#

"""
The gpsubprocess is a subclass of subprocess that allows for non-blocking
processing of status and servicing of stdout and stderr.  

Also the aim was to reduce the overhead associated with this servicing.
Normal subprocess.communicate() results in up to 3 threads being created 
(stdin,stdout,stderr) and then a blocking wait for the process and threads
to finish.  This doesn't allow the user to be able to cancel long running
tasks.


"""
import errno
import fcntl
import os
import select
import time
try:
    import subprocess32 as subprocess
except:
    import subprocess
from gppylib import gplog


logger=gplog.get_default_logger()


class Popen(subprocess.Popen):
    
    cancelRequested=False

    
    def communicate2(self, timeout=2,input=None):
        """ An extension to communicate() that allows for external cancels
        to abort processing.  

        All internal I/O calls are non-blocking.

        The timeout is in seconds and is the max. amount of time to wait in 
        select() for something to read from either stdout or stderr.  This 
        then effects how responsive it will be to cancel requests.
        """
        terminated=False
        
        output = []
        error = []

        self._setupNonblocking()

        if self.stdin:
            if input:
                self.stdin.write(input)

            # ESCALATION-151 - always close stdin, even when no input from caller
            self.stdin.close()
                
        while not (terminated or self.cancelRequested):
            terminated = self._check_status()

            if not terminated:
                self._read_files(timeout,output,error)

        # Consume rest of output
        self._finish_read_files(timeout,output,error)
                      
        (resout,reserr)=self._postprocess_outputs(output,error)

        return (self.returncode,resout,reserr)


    def cancel(self):
        """Sets a flag that will cause execution to halt during the next 
        select cycle.
        
        This amount of time is based on the timeout specified.
        """
        logger.debug("cancel is requested")
        self.cancelRequested=True
        
        

    
    def _setupNonblocking(self):
        """ sets stdout and stderr  fd's to be non-blocking.
        The fcntl throws an IOError if these calls fail. 
        """        
        fcntl.fcntl(self.stdout, fcntl.F_SETFL, os.O_NDELAY | os.O_NONBLOCK)
        fcntl.fcntl(self.stderr, fcntl.F_SETFL, os.O_NDELAY | os.O_NONBLOCK)

                
    def _postprocess_outputs(self,output,error):
        # All data exchanged.  Translate lists into strings.
        if output is not None:
            output = ''.join(output)
        if error is not None:
            error = ''.join(error)

        # Translate newlines, if requested.  We cannot let the file
        # object do the translation: It is based on stdio, which is
        # impossible to combine with select (unless forcing no
        # buffering).
        if self.universal_newlines and hasattr(file, 'newlines'):
            if output:
                output = self._translate_newlines(output)
            if error:
                error = self._translate_newlines(error)    
        return (output,error)
    
    
    def _read_files(self,timeout,output,error):
        readList=[]
        readList.append(self.stdout)
        readList.append(self.stderr)
        rset = self.__poll(readList, timeout)
        
        if self.stdout.fileno() in rset:
            output.append(os.read(self.stdout.fileno(),8192))

        if self.stderr.fileno() in rset:
            error.append(os.read(self.stderr.fileno(),8192))
            
    
    def _finish_read_files(self, timeout, output, error):
        """This function reads the rest of stderr and stdout and appends
        it to error and output.  This ensures that all output is received"""
        bytesRead=0
        
        # consume rest of output
        try:
            rset = self.__poll([self.stdout], timeout)
            while (self.stdout.fileno() in rset):
                buffer = os.read(self.stdout.fileno(), 8192)
                if buffer == '':
                    break
                else:
                    output.append(buffer)
                rset = self.__poll([self.stdout], timeout)
        except OSError:
            # Pipe closed when we tried to read.  
            pass 
    
        try:
            rset = self.__poll([self.stderr], timeout)    
            while (self.stderr.fileno() in rset):
                buffer = os.read(self.stderr.fileno(), 8192)
                if buffer == '':
                    break
                else:
                    error.append(buffer)
                rset = self.__poll([self.stderr], timeout)
        except OSError:
            # Pipe closed when we tried to read.
            pass 
            


        """ Close stdout and stderr PIPEs """
        self.stdout.close()
        self.stderr.close()


    def _check_status(self):
        terminated=False
        """Another possibility for the below line would be to try and capture
        rusage information.  Perhaps that type of call would be an external
        method for users to check on status:        
        (pid, status, rusage)=os.wait4(self.pid, os.WNOHANG)
        """
        (pid,status)=os.waitpid(self.pid, os.WNOHANG)
        

        if pid == 0:
            #means we are still in progress
            return

        exitstatus = os.WEXITSTATUS(status)
        if os.WIFEXITED (status):            
            self.exitstatus = os.WEXITSTATUS(status)
            self.signalstatus = None
            terminated = True
        elif os.WIFSIGNALED (status):
            self.exitstatus = None
            self.signalstatus = os.WTERMSIG(status)
            terminated = True
        elif os.WIFSTOPPED (status):
            raise Exception('Wait was called for a child process that is stopped.\
                             This is not supported. Is some other process attempting\
                             job control with our child pid?')

        self._handle_exitstatus(status)

        return terminated


    def __poll (self, iwtd, timeout=None):
        """This is a wrapper around select.poll() that ignores signals. 
        
        If select.poll raises a InterruptedError exception and errno is an EINTR
        error then it is ignored. 
        
        """        
        if timeout is not None:
            end_time = time.time() + timeout
           
        poller = select.poll()            
        for fd in iwtd:
            poller.register(fd)

        while True:
            try:
                timeout_ms = None if timeout is None else timeout * 1000
                results = poller.poll(timeout_ms)
                return [fd for fd, _ in results]
            except InterruptedError:
                err = sys.exc_info()[1]
                if err.args[0] == errno.EINTR:
                    # if we loop back we have to subtract the
                    # amount of time we already waited.
                    if timeout is not None:
                        timeout = end_time - time.time()
                        if timeout < 0:
                            return ([])
                    else:
                        # something else caused the select.error, so
                        # this actually is an exception.
                        raise

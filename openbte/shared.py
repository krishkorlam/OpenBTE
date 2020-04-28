from __future__ import absolute_import
import numpy as np
from scipy.sparse.linalg import splu
from termcolor import colored, cprint 
from .utils import *
import deepdish as dd
from mpi4py import MPI
import scipy.sparse as sp
import time

comm = MPI.COMM_WORLD


class Solver(object):

  def __init__(self,**argv):

        #COMMON OPTIONS------------
        self.data = argv
        self.tt = np.float64
        self.state = {}
        self.multiscale = argv.setdefault('multiscale',False)
        self.verbose = argv.setdefault('verbose',True)
        self.alpha = argv.setdefault('alpha',1.0)
        #----------------------------

        #-----IMPORT MESH--------------------------------------------------------------
        if comm.rank == 0:
         if 'geometry' in argv.keys():
          self.mesh = argv['geometry'].data
         else: 
          self.mesh = dd.io.load('geometry.h5')
         #-----------------
         self.i  = self.mesh['i']
         self.j  = self.mesh['j']
         self.k = self.mesh['k']
         self.db = self.mesh['db']
         self.eb = self.mesh['eb']
         self.kappa_mask = self.mesh['kappa_mask']
         self.pp = self.mesh['pp']
         self.meta = self.mesh['meta']
         self.im = np.concatenate((self.mesh['i'],list(np.arange(self.mesh['meta'][0]))))
         self.jm = np.concatenate((self.mesh['j'],list(np.arange(self.mesh['meta'][0]))))
        self.create_shared_memory(['i','j','im','jm','db','k','eb','kappa_mask','pp','meta'])
        self.n_elems = int(self.meta[0])
        self.kappa_factor = self.meta[1]
        self.dim = int(self.meta[2])
        #------------------------------------------------------------------------------
    
        if comm.rank == 0:
         if self.verbose: self.print_logo()

        if comm.rank == 0:
          self.mat = dd.io.load('material.h5')
          self.kappa = self.mat['kappa']
          data = self.solve_fourier_new(self.kappa,**argv)
          variables = {0:{'name':'Temperature Fourier','units':'K',        'data':data['temperature']},\
                     1:{'name':'Flux Fourier'       ,'units':'W/m/m/K','data':data['flux']}}
          self.state.update({'variables':variables,\
                           'kappa_fourier':data['kappa']})
          temperature_fourier = data['temperature']
          self.kappa_fourier = np.array([data['kappa']])

          print('                        MATERIAL                 ')   
          print(colored(' -----------------------------------------------------------','green'))
          print(colored('  Bulk Thermal Conductivity [W/m/K]:       ','green')+ str(round(self.mat['kappa'][0,0],4)))
          print(colored('  Fourier Thermal Conductivity [W/m/K]:    ','green') + str(round(data['kappa'],4)))
          print(colored(' -----------------------------------------------------------','green'))
        else: temperature_fourier = None
        self.temperature_fourier = comm.bcast(temperature_fourier,root=0)

         
        self.create_shared_memory(['kappa_fourier'])
        self.only_fourier = argv.setdefault('only_fourier',False)
       
        if not self.only_fourier:
         
         if comm.rank == 0:

          self.tc = np.array(self.mat['temp'])
          self.sigma = self.mat['G']*1e9
          self.VMFP = self.mat['F']*1e9 
          self.BM = np.zeros(1)
          if self.tc.ndim == 1:
            self.coll = True
            self.meta = np.array([1,len(self.tc),1])
            self.tc = np.array([self.tc])
            B = self.mat['B']
            B += B.T - 0.5*np.diag(np.diag(B))
            self.BM = np.einsum('i,ij->ij',self.mat['scale'],B)
            self.sigma = np.array([self.sigma])
            self.VMFP = np.array([self.VMFP]) 
          else: 
            self.meta = np.array([self.tc.shape[0],self.tc.shape[1],0])

         self.create_shared_memory(['sigma','VMFP','tc','meta','BM'])
         self.n_serial = self.meta[0]           
         self.n_parallel = self.meta[1]           
         self.coll = bool(self.meta[2])

         #---------------------------------------------------
         block =  self.n_parallel//comm.size
         if comm.rank == comm.size-1: 
          self.rr = range(block*comm.rank,self.n_parallel)
         else: 
          self.rr = range(block*comm.rank,block*(comm.rank+1))
  
         #--------------------------------     
         block =  self.n_serial//comm.size
         if comm.rank == comm.size-1: 
          self.ff = range(block*comm.rank,self.n_serial)
         else: 
          self.ff = range(block*comm.rank,block*(comm.rank+1))
         #--------------------------------
         if comm.rank == 0:
           print()
           print('      Iter    Thermal Conductivity [W/m/K]      Error ''')
           print(colored(' -----------------------------------------------------------','green'))

         if self.coll:    
          data = self.solve_bte(**argv)
         else:
          data = self.solve_mfp(**argv)

         if comm.rank == 0:
          variables = self.state['variables']

          variables[2]    = {'name':'Temperature BTE','units':'K'             ,'data':data['temperature']}
          variables[3]    = {'name':'Flux BTE'       ,'units':'W/m/m/K'       ,'data':data['flux']}

          self.state.update({'variables':variables,\
                           'kappa':data['kappa_vec']})


        if comm.rank == 0:
         if argv.setdefault('save',True):
          dd.io.save('solver.h5',self.state)
         if self.verbose:
          print(' ')   
          print(colored('                 OpenBTE ended successfully','green'))
          print(' ')  

  def mesh_info(self):

          print('                           Spatial Mesh                 ')   
          print(colored(' -----------------------------------------------------------','green'))
          print(colored('  Dimension:                   ','green') + str(self.dim))
          print(colored('  Number of Elements:          ','green') + str(self.n_elems))
          print(colored('  Number of Sides:             ','green') + str(len(self.mesh['sides'])))
          print(colored('  Number of Nodes:             ','green') + str(len(self.mesh['nodes'])))
          print(colored(' -----------------------------------------------------------','green'))



  def create_shared_memory(self,varss):
       for var in varss:
         #--------------------------------------
         if comm.Get_rank() == 0: 
          tmp = eval('self.' + var)
          if tmp.dtype == np.int64:
              data_type = 0
              itemsize = MPI.INT.Get_size() 
          elif tmp.dtype == np.float64:
              data_type = 1
              itemsize = MPI.DOUBLE.Get_size() 
          else:
              print('data type for shared memory not supported')
              quit()
          size = np.prod(tmp.shape)
          nbytes = size * itemsize
          meta = [tmp.shape,data_type,itemsize]
         else: nbytes = 0; meta = None
         meta = comm.bcast(meta,root=0)

         #ALLOCATING MEMORY---------------
         win = MPI.Win.Allocate_shared(nbytes,meta[2], comm=comm) 
         buf,itemsize = win.Shared_query(0)
         assert itemsize == meta[2]
         dt = 'i' if meta[1] == 0 else 'd'
         output = np.ndarray(buffer=buf,dtype=dt,shape=meta[0]) 

         if comm.rank == 0:
             output[:] = tmp  

         exec('self.' + var + '=output')





  def solve_mfp(self,**argv):


     if comm.rank == 0:   
      SS = np.zeros(1)
      Gbp = np.zeros(1)
      if len(self.mesh['db']) > 0:
       Gbm2 = np.einsum('mqj,jn->mqn',self.VMFP ,self.mesh['db'],optimize=True).clip(max=0)
       Gb   = np.einsum('mqj,jn->mqn',self.sigma,self.mesh['db'],optimize=True)
       Gbp = Gb.clip(min=0); Gbm = Gb.clip(max=0)
       with np.errstate(divide='ignore', invalid='ignore'):
         tmp = 1/Gbm.sum(axis=1); tmp[np.isinf(tmp)] = 0
       SS = np.einsum('mqc,mc->mqc',Gbm2,tmp)
      #---------------------------------------------------------------
      data1 = {'Gbp':Gbp}
      data2 = {'SS':SS}
     else: data1 = None; data2 = None 
     data1 = comm.bcast(data1,root = 0)
     data2 = comm.bcast(data2,root = 0)
     Gbp = data1['Gbp']
     SS = data2['SS']

     #Main matrix----
     G = np.einsum('mqj,jn->mqn',self.VMFP[:,self.rr],self.k,optimize=True)
     Gp = G.clip(min=0); Gm = G.clip(max=0)

     D = np.ones((self.n_serial,len(self.rr),self.n_elems))
     for n,i in enumerate(self.i): 
         D[:,:,i] += Gp[:,:,n]
     if len(self.db) > 0: #boundary
      Gb = np.einsum('mqj,jn->mqn',self.VMFP[:,self.rr],self.db,optimize=True)
      Gbp2 = Gb.clip(min=0);
      for n,i in enumerate(self.eb): D[:,:,i]  += Gbp2[:,:,n]

     A = np.concatenate((Gm,D),axis=2)

     lu =  {}
     DeltaT = self.temperature_fourier
     kappa_vec = list(self.kappa_fourier)

     kappa_old = kappa_vec[-1]
     error = 1
     kk = 0

     kappa_tot = np.zeros(1)
     MM = np.zeros(1)
     Mp = np.zeros(1)
     kappap = np.zeros((self.n_serial,self.n_parallel))
     kappa = np.zeros((self.n_serial,self.n_parallel))
     tf = np.zeros((self.n_serial,self.n_elems))
     tfg = np.zeros((self.n_serial,self.n_elems,3))
     tfp = np.zeros((self.n_serial,self.n_elems))
     tfgp = np.zeros((self.n_serial,self.n_elems,3))
     termination = True
     if self.multiscale:
      mfp_ave = np.sqrt(3*self.mat['mfp_average'])*1e9
     kappafp = np.zeros((self.n_serial,self.n_parallel));kappaf = np.zeros((self.n_serial,self.n_parallel))


     #if comm.rank == 0:
     # self.DeltaTNew = np.zeros(self.n_elems)
     # self.DeltaT = self.temperature_fourier
     #self.create_shared_memory(['DeltaTNew','DeltaT'])
      
     Bm = np.zeros((self.n_serial,self.n_parallel,len(self.eb)))   
     if len(self.db) > 0: 
        for n,i in enumerate(self.eb): 
          Bm[:,self.rr,n] += DeltaT[i]*np.einsum('mu,mq->mq',Gbp[:,:,n],SS[:,self.rr,n],optimize=True)

     while kk < self.data.setdefault('max_bte_iter',100) and error > self.data.setdefault('max_bte_error',1e-2):

        DeltaTp = np.zeros_like(DeltaT)
        if self.multiscale:
         for n,m in enumerate(self.ff):
           dataf = self.solve_fourier_new(self.mat['mfp_average'][m]*1e-18,**argv,pseudo=DeltaT)
           tfp[m] = dataf['temperature']
           tfgp[m] = dataf['grad']
           for q in range(self.n_parallel): 
            kappafp[m,q] = -np.dot(self.mesh['kappa_mask'],dataf['temperature'] - np.dot(self.VMFP[m,q],dataf['grad'].T))
         comm.Allreduce([kappafp,MPI.DOUBLE],[kappaf,MPI.DOUBLE],op=MPI.SUM)
         comm.Allreduce([tfp,MPI.DOUBLE],[tf,MPI.DOUBLE],op=MPI.SUM)
         comm.Allreduce([tfgp,MPI.DOUBLE],[tfg,MPI.DOUBLE],op=MPI.SUM)

        #Multiscale scheme-----------------------------
        diffusive = 0
        #DeltaTp = np.zeros(self.n_elems)   
        Jp = np.zeros((self.n_elems,3))
        J = np.zeros((self.n_elems,3))
        Bmp = np.zeros_like(Bm)
        for n,q in enumerate(self.rr): 
           fourier = False
           for m in range(self.n_serial)[::-1]:
              if fourier:
               kappap[m,q] = kappaf[m,q]
               Xp[m,q] = tf[m] - np.dot(self.VMFP[m,q],tfg[m].T)
               diffusive +=1
              else: 
               if not (m,q) in lu.keys() :
                lu_loc = sp.linalg.splu(sp.csc_matrix((A[m,n],(self.im,self.jm)),shape=(self.n_elems,self.n_elems),dtype=self.tt))
                if argv.setdefault('keep_lu',True):
                 lu.update({(m,q):lu_loc})
               else: lu_loc   = lu[(m,q)]

               #reconstruct RHS---
               P = np.zeros(self.n_elems)
               for ss,v in self.pp:
                   P[self.i[int(ss)]] = -Gm[m,n,int(ss)]*v

               RHS = DeltaT + P
               for c,i in enumerate(self.eb): RHS[i] += Bm[m,q,c]
               #--------------------------
               X = lu_loc.solve(RHS) 
               kappap[m,q] = -np.dot(self.kappa_mask,X)
               
               DeltaTp += X*self.tc[m,q]
               Jp += np.outer(X,self.sigma[m,q])*1e-18

               #------------------------
               if len(self.db) > 0:
                for c,i in enumerate(self.eb):
                  Bmp[m,:,c] += X[i]*Gbp[m,q,c]*SS[m,:,c]

               if abs(kappap[m,q] - kappaf[m,q])/abs(kappap[m,q]) < 0.015 and self.multiscale:
                  kappap[m,q] = kappaf[m,q]
                  diffusive +=1
                  fourier=True
               else:   
                   if self.multiscale and m == 0:
                       termination = False
        Mp[0] = diffusive
        comm.Barrier()


        comm.Allreduce([DeltaTp,MPI.DOUBLE],[DeltaT,MPI.DOUBLE],op=MPI.SUM)
        comm.Allreduce([Jp,MPI.DOUBLE],[J,MPI.DOUBLE],op=MPI.SUM)
        comm.Allreduce([Bmp,MPI.DOUBLE],[Bm,MPI.DOUBLE],op=MPI.SUM)
        comm.Allreduce([kappap,MPI.DOUBLE],[kappa,MPI.DOUBLE],op=MPI.SUM)
        comm.Allreduce([Mp,MPI.DOUBLE],[MM,MPI.DOUBLE],op=MPI.SUM)
                                      

        #-----------------------------------------------
        kappa_totp = np.array([np.einsum('mq,mq->',self.sigma[:,self.rr,0],kappa[:,self.rr])])*self.kappa_factor*1e-18
        comm.Allreduce([kappa_totp,MPI.DOUBLE],[kappa_tot,MPI.DOUBLE],op=MPI.SUM)
        kk +=1

        error = abs(kappa_old-kappa_tot[0])/abs(kappa_tot[0])
        kappa_old = kappa_tot[0]
        kappa_vec.append(kappa_tot[0])
        if self.verbose and comm.rank == 0:   
         print('{0:8d} {1:24.4E} {2:22.4E}'.format(kk,kappa_vec[-1],error))

     if self.verbose and comm.rank == 0:
      print(colored(' -----------------------------------------------------------','green'))


     if self.multiscale and comm.rank == 0:
        print()
        print('                  Multiscale Diagnostics        ''')
        print(colored(' -----------------------------------------------------------','green'))

        diff = int(MM[0])/self.n_serial/self.n_parallel 
        print(colored(' BTE:              ','green') + str(round((1-diff)*100,2)) + ' %' )
        print(colored(' FOURIER:          ','green') + str(round(diff*100,2)) + ' %' )
        print(colored(' Full termination: ','green') + str(termination) )
        print(colored(' -----------------------------------------------------------','green'))

     return {'kappa_vec':kappa_vec,'temperature':DeltaT,'flux':J}


  def solve_bte(self,**argv):


     if comm.rank == 0:   
      SS = np.zeros(1)
      Gbp = np.zeros(1)
      if len(self.mesh['db']) > 0:
       Gb = np.einsum('mqj,jn->mqn',self.VMFP,self.mesh['db'],optimize=True)
       Gbp = Gb.clip(min=0); Gbm2 = Gb.clip(max=0)
       Gb = np.einsum('mqj,jn->mqn',self.sigma,self.mesh['db'],optimize=True)
       Gbp = Gb.clip(min=0); Gbm = Gb.clip(max=0)

       if self.coll:   
        SS  = np.einsum('mqc,c->mqc',Gbm2,1/Gbm.sum(axis=0).sum(axis=0))
       else: 
        with np.errstate(divide='ignore', invalid='ignore'):
         tmp = 1/Gbm.sum(axis=1)
         tmp[np.isinf(tmp)] = 0
        SS = np.einsum('mqc,mc->mqc',Gbm2,tmp)
      #---------------------------------------------------------------
      data1 = {'Gbp':Gbp}
      data2 = {'SS':SS}
     else: data1 = None; data2 = None 
     data1 = comm.bcast(data1,root = 0)
     data2 = comm.bcast(data2,root = 0)
     Gbp = data1['Gbp']
     SS = data2['SS']

     #Main matrix----
     G = np.einsum('mqj,jn->mqn',self.VMFP[:,self.rr],self.k,optimize=True)
     Gp = G.clip(min=0); Gm = G.clip(max=0)

     D = np.ones((self.n_serial,len(self.rr),self.n_elems))

     for n,i in enumerate(self.i): 
         D[:,:,i] += Gp[:,:,n]
     if len(self.db) > 0:
      Gb = np.einsum('mqj,jn->mqn',self.VMFP[:,self.rr],self.db,optimize=True)
      Gbp2 = Gb.clip(min=0);
      for n,i in enumerate(self.eb): D[:,:,i]  += Gbp2[:,:,n]

     A = np.concatenate((Gm,D),axis=2)

     lu =  {}

     X = np.tile(self.temperature_fourier,(self.n_serial,self.n_parallel,1))
     X_old = X.copy()
     kappa_vec = list(self.kappa_fourier)
     kappa_old = kappa_vec[-1]
     alpha = self.data.setdefault('alpha',1)
     error = 1
     kk = 0

     Xp = np.zeros_like(X)
     Bm = np.zeros((self.n_parallel,self.n_elems))
     DeltaT = np.zeros(self.n_elems)   

     kappa_tot = np.zeros(1)
     MM = np.zeros(1)
     Mp = np.zeros(1)
     kappa = np.zeros((self.n_serial,self.n_parallel))

     while kk < self.data.setdefault('max_bte_iter',100) and error > self.data.setdefault('max_bte_error',1e-2):

       kappap = np.zeros((self.n_serial,self.n_parallel))
      # COMMON----- 
       Bm = np.zeros((self.n_serial,len(self.rr),self.n_elems))   
       if len(self.db) > 0: 
         for n,i in enumerate(self.eb):
               Bm[:,:,i] +=np.einsum('mu,mu,lq->lq',X[:,:,i],Gbp[:,:,n],SS[:,self.rr,n],optimize=True)
       
       DeltaT = np.matmul(self.BM[self.rr],alpha*X[0]+(1-alpha)*X_old[0]) 
       for n,i in enumerate(self.rr):

            if not i in lu.keys() :
                lu_loc = sp.linalg.splu(sp.csc_matrix((A[0,n],(self.im,self.jm)),shape=(self.n_elems,self.n_elems),dtype=self.tt))
                if argv.setdefault('keep_lu',True):
                 lu.update({i:lu_loc})
            else: lu_loc   = lu[i]
            
            #PERIODIC--
            P = np.zeros(self.n_elems)
            for ss,v in self.pp:  P[self.i[int(ss)]] = -Gm[0,n,int(ss)]*v
            #---------

            Xp[0,i] = lu_loc.solve(DeltaT[n] + Bm[0,n] + P)
            kappap[0,i] -= np.dot(self.kappa_mask,Xp[0,i])

       comm.Allreduce([kappap,MPI.DOUBLE],[kappa,MPI.DOUBLE],op=MPI.SUM)
       comm.Allreduce([Xp,MPI.DOUBLE],[X,MPI.DOUBLE],op=MPI.SUM)

       kappa_totp = np.array([np.einsum('mq,mq->',self.sigma[:,self.rr,0],kappa[:,self.rr])])*self.kappa_factor*1e-18
       comm.Allreduce([kappa_totp,MPI.DOUBLE],[kappa_tot,MPI.DOUBLE],op=MPI.SUM)


       error = abs(kappa_old-kappa_tot[0])/abs(kappa_tot[0])
       kappa_old = kappa_tot[0]
       kappa_vec.append(kappa_tot[0])
       if self.verbose and comm.rank == 0:   
        print('{0:8d} {1:24.4E} {2:22.4E}'.format(kk,kappa_vec[-1],error))
       kk+=1

     if self.verbose and comm.rank == 0:
      print(colored(' -----------------------------------------------------------','green'))

     
     T = np.einsum('mqc,mq->c',X,self.tc)
     J = np.einsum('mqj,mqc->cj',self.sigma,X)*1e-18
     return {'kappa_vec':kappa_vec,'temperature':T,'flux':J}



  def get_decomposed_directions(self,i,j,rot=np.eye(3)):

     normal = self.mesh['normals'][i][j]
     dist   = self.mesh['dists'][i][j]
     v_orth = np.dot(normal,np.dot(rot,normal))/np.dot(normal,dist)
     v_non_orth = np.dot(rot,normal) - dist*v_orth
     return v_orth,v_non_orth

  def get_kappa(self,i,j,ll,kappa):

   if i ==j:
    return np.array(kappa[i])
   
   normal = self.mesh['normals'][i][j]

   kappa_i = np.array(kappa[i])
   kappa_j = np.array(kappa[j])

   ki = np.dot(normal,np.dot(kappa_i,normal))
   kj = np.dot(normal,np.dot(kappa_j,normal))
   w  = self.mesh['interp_weigths'][ll][0]

   kappa_loc = kj*kappa_i/(ki*(1-w) + kj*w)
 
   return kappa_loc

   
  def assemble_modified_fourier(self):

    F = sp.dok_matrix((self.n_elems,self.n_elems))
    B = np.zeros(self.n_elems)
    for ll in self.mesh['side_list']['active']:
      area = self.mesh['areas'][ll]  
      (i,j) = self.mesh['side_elem_map'][ll]
      vi = self.mesh['volumes'][i]
      vj = self.mesh['volumes'][j]
      kappa = self.get_kappa(i,j,ll)
      if not i == j:
       (v_orth,dummy) = self.get_decomposed_directions(i,j)
       F[i,i] += v_orth/vi*area
       F[i,j] -= v_orth/vi*area
       F[j,j] += v_orth/vj*area
       F[j,i] -= v_orth/vj*area
       if ll in self.mesh['side_list']['Periodic']:
        B[i] += self.mesh['periodic_side_values'][ll]*v_orth/vi*area
        B[j] -= self.mesh['periodic_side_values'][ll]*v_orth/vj*area
    self.mfe = {'Af':F.tocsc(),'Bf':B}



  def solve_fourier_new(self,kappa,**argv):

    if np.isscalar(kappa):
       kappa = np.diag(np.diag(kappa*np.eye(3)))

    if kappa.ndim == 2:
      kappa = np.repeat(np.array([np.diag(np.diag(kappa))]),self.n_elems,axis=0)

    F = sp.dok_matrix((self.n_elems,self.n_elems))
    B = np.zeros(self.n_elems)
 
    for ll in self.mesh['side_list']['active']:
      area = self.mesh['areas'][ll]  
      (i,j) = self.mesh['side_elem_map'][ll]
      vi = self.mesh['volumes'][i]
      vj = self.mesh['volumes'][j]
      kappa_loc = self.get_kappa(i,j,ll,kappa)
      if not i == j:
       (v_orth,dummy) = self.get_decomposed_directions(i,j,rot=kappa_loc)
       F[i,i] += v_orth/vi*area
       F[i,j] -= v_orth/vi*area
       F[j,j] += v_orth/vj*area
       F[j,i] -= v_orth/vj*area
       if ll in self.mesh['side_list']['Periodic']:
        B[i] += self.mesh['periodic_side_values'][ll]*v_orth/vi*area
        B[j] -= self.mesh['periodic_side_values'][ll]*v_orth/vj*area
    
    #rescaleand fix one point to 0
    F = F.tocsc()
    if 'pseudo' in argv.keys():
      F = F + sp.eye(self.n_elems)
      B = B + argv['pseudo']
      scale = 1/F.max(axis=0).toarray()[0]
      F.data = F.data * scale[F.indices]
    else:  
      scale = 1/F.max(axis=0).toarray()[0]
      n = np.random.randint(self.n_elems)
      scale[n] = 0
      F.data = F.data * scale[F.indices]
      F[n,n] = 1
      B[n] = 0
    #-----------------------

    SU = splu(F)

    C = np.zeros(self.n_elems)
    
    n_iter = 0
    kappa_old = 0
    error = 1  
    grad = np.zeros((self.n_elems,3))
    while error > argv.setdefault('max_fourier_error',1e-4) and \
                  n_iter < argv.setdefault('max_fourier_iter',10) :
        RHS = B + C
        for n in range(self.n_elems):
          RHS[n] = RHS[n]*scale[n]  

        temp = SU.solve(RHS)
        temp = temp - (max(temp)+min(temp))/2.0
        kappa_eff = self.compute_diffusive_thermal_conductivity(temp,grad,kappa)
        error = abs((kappa_eff - kappa_old)/kappa_eff)
        kappa_old = kappa_eff
        n_iter +=1
        grad = self.compute_grad(temp)
        C = self.compute_non_orth_contribution(grad,kappa)
    flux = -np.einsum('cij,cj->ci',kappa,grad)

    return {'flux':flux,'temperature':temp,'kappa':kappa_eff,'grad':grad}

  def compute_grad(self,temp):

   diff_temp = self.n_elems*[None]
   for i in range(len(diff_temp)):
      diff_temp[i] = len(self.mesh['elems'][i])*[0] 

   gradT = np.zeros((self.n_elems,3))
   for ll in self.mesh['side_list']['active'] :
    elems = self.mesh['side_elem_map'][ll]

    kc1 = elems[0]
    c1 = self.mesh['centroids'][kc1]

    ind1 = list(self.mesh['elem_side_map'][kc1]).index(ll)

    if not ll in self.mesh['side_list']['Boundary']:

     kc2 = elems[1]
     ind2 = list(self.mesh['elem_side_map'][kc2]).index(ll)
     temp_1 = temp[kc1]
     temp_2 = temp[kc2]

     if ll in self.mesh['side_list']['Periodic']:
      temp_2 += self.mesh['periodic_side_values'][ll]

     diff_t = temp_2 - temp_1
     
     diff_temp[kc1][ind1]  = diff_t
     diff_temp[kc2][ind2]  = -diff_t

   
   for k in range(self.n_elems) :
    tmp = np.dot(self.mesh['weigths'][k],diff_temp[k])
    gradT[k,0] = tmp[0] #THESE HAS TO BE POSITIVE
    gradT[k,1] = tmp[1]
    if self.mesh['dim'] == 3:
     gradT[k,2] = tmp[2]

   return gradT  


  def compute_non_orth_contribution(self,gradT,kappa) :

    C = np.zeros(self.n_elems)

    for ll in self.mesh['side_list']['active']:

     (i,j) = self.mesh['side_elem_map'][ll]

     if not i==j:

      area = self.mesh['areas'][ll]   
      w  = self.mesh['interp_weigths'][ll][0]
      #F_ave = w*np.dot(gradT[i],self.mat['kappa']) + (1.0-w)*np.dot(gradT[j],self.mat['kappa'])
      F_ave = w*np.dot(gradT[i],kappa[i]) + (1.0-w)*np.dot(gradT[j],kappa[j])
      grad_ave = w*gradT[i] + (1.0-w)*gradT[j]

      (_,v_non_orth) = self.get_decomposed_directions(i,j)#,rot=self.mat['kappa'])

      C[i] += np.dot(F_ave,v_non_orth)/2.0/self.mesh['volumes'][i]*area
      C[j] -= np.dot(F_ave,v_non_orth)/2.0/self.mesh['volumes'][j]*area

    return C


  def compute_diffusive_thermal_conductivity(self,temp,gradT,kappa):

   kappa_eff = 0
   for l in self.mesh['flux_sides']:

    (i,j) = self.mesh['side_elem_map'][l]
    #(v_orth,v_non_orth) = self.get_decomposed_directions(i,j,rot=self.mat['kappa'])
    (v_orth,v_non_orth) = self.get_decomposed_directions(i,j,rot=self.get_kappa(i,j,l,kappa))

    deltaT = temp[i] - (temp[j] + 1) 
    kappa_eff -= v_orth *  deltaT * self.mesh['areas'][l]
    w  = self.mesh['interp_weigths'][l][0]
    grad_ave = w*gradT[i] + (1.0-w)*gradT[j]
    kappa_eff += np.dot(grad_ave,v_non_orth)/2 * self.mesh['areas'][l]

   return kappa_eff*self.kappa_factor

  def print_logo(self):


    #v = pkg_resources.require("OpenBTE")[0].version   
    print(' ')
    print(colored(r'''        ___                   ____ _____ _____ ''','green'))
    print(colored(r'''       / _ \ _ __   ___ _ __ | __ )_   _| ____|''','green'))
    print(colored(r'''      | | | | '_ \ / _ \ '_ \|  _ \ | | |  _|  ''','green'))
    print(colored(r'''      | |_| | |_) |  __/ | | | |_) || | | |___ ''','green'))
    print(colored(r'''       \___/| .__/ \___|_| |_|____/ |_| |_____|''','green'))
    print(colored(r'''            |_|                                ''','green'))
    print()
    print('                       GENERAL INFO')
    print(colored(' -----------------------------------------------------------','green'))
    print(colored('  Contact:          ','green') + 'romanog@mit.edu                       ') 
    print(colored('  Source code:      ','green') + 'https://github.com/romanodev/OpenBTE  ')
    print(colored('  Become a sponsor: ','green') + 'https://github.com/sponsors/romanodev ')
    print(colored('  Cloud:            ','green') + 'https://shorturl.at/cwDIP             ')
    print(colored('  Mailing List:     ','green') + 'https://shorturl.at/admB0             ')
    print(colored(' -----------------------------------------------------------','green'))
    print()   


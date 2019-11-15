"""
 produces a more generalised diagnostic over multiple runs using multiple
 numbers of agents for arc_ukf.py only. 
 This produces a chloropleth style map showing the grand mean error
 over both time and agents for various fixed numbers of agents 
 and proportions observed.
"""
import pickle
import sys
import os
sys.path.append("../../stationsim")
sys.path.append("../..")

from stationsim.ukf import ukf,ukf_ss,plots

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from mpl_toolkits.axes_grid1 import make_axes_locatable
import matplotlib.cm as cm
import matplotlib.colors as col
import matplotlib.patheffects as pe

import glob
import seaborn as sns
import pandas as pd

plt.rcParams.update({'font.size':20})


#plt.style.use("dark_background")
        

def grand_depickle_ukf_data_parser(instance):
    """PUll data from aggregate ukf class into nice arrays
    Parameters
    ------
    instance : class
    
    Returns
    ------
    b,c,d,nan_array : array_like
        `b` UKF predictions every sample rate time steps. All other elements nan
        `c` Full UKF predictions. Say we assimilate every 5 time points then 4 
            are just ABM forecasts and the 5th are assimilated values. Useful
            for animations
        `d` Full true agent positions for comparison
        `nan_array` which elements are nan good for accurate plots/error metrics`
    """
    
    sample_rate = instance.sample_rate
    
    nan_array = np.ones(shape=(max([len(agent.history_locations) for 
                                    agent in instance.base_model.agents]),
                                    2*instance.pop_total))*np.nan
    for i in range(instance.pop_total):
        agent = instance.base_model.agents[i]
        array = np.array(agent.history_locations)
        array[array==None] ==np.nan
        nan_array[:len(agent.history_locations),2*i:(2*i)+2] = array
    
    nan_array = ~np.isnan(nan_array)
    
    b2 = np.vstack(instance.ukf_histories)
    d = np.vstack(instance.truths)

    
    b= np.zeros((d.shape[0],b2.shape[1]))*np.nan
  
    for j in range(int(b.shape[0]//sample_rate)):
        b[j*sample_rate,:] = b2[j,:]
     
    if sample_rate>1:
        c= np.vstack(instance.ukf_preds)

        return b,c,d,nan_array
    else:
        return b,d,nan_array

def l2_parser(instance,prop):
    """gets real and UKF predicted data. Measures L2 distances between them
        
        Parameters
        ------
        instance : class
        
        Returns
        ------
        distance_obs : array_like
            `distance_obs` numpy array of distance between agents true positions 
            and their respective UKF predictions

    """      
    if instance.filter_params["sample_rate"]==1:
            preds,truth,nan_array = grand_depickle_ukf_data_parser(instance)
    else:
        preds,full_preds,truth,nan_array = grand_depickle_ukf_data_parser(instance)
        full_preds[~nan_array]=np.nan #make empty values to prevent mean skewing in diagnostic plots

    truth[~nan_array]=np.nan #make empty values to prevent mean skewing in diagnostic plots
    preds[~nan_array]=np.nan #make empty values to prevent mean skewing in diagnostic plots

    plts = plots(instance,"ukf_results/")
    true_u,b_u,plot_range = plts.plot_data_parser(truth,preds,False)
    true_o,b_o,plot_range = plts.plot_data_parser(truth,preds,True)    

    distances_obs,oindex,agent_means,t_mean_obs = plts.L2s(true_o,b_o)
    if prop<1:
        distances_uobs,uindex,agent_means,t_mean_uobs = plts.L2s(true_u,b_u)
    else:
        distances_uobs = []
    
    return preds,distances_obs,distances_uobs



def grand_L2_matrix(n,prop): 
    """produces grand median matrix for all 30 ABM runs for choropleth plot
    
    Parameters
    ------
    n,prop : float
        population `n` and proportion `prop`
    
    Returns
    ------
    L2 : array_like
        `L2` matrix of grand medians. each row is a population each column is a proportion
    

    """        
    "empty frames"
    o_L2 = np.ones((len(n),len(prop)))*np.nan
    u_L2 = np.ones((len(n),len(prop)))*np.nan
    
    "cycle over number of agents and proportions. taking grand (mean of means) L2 mean for each pair"
    for i,num in enumerate(n):
        files={}
        for j in prop:
            if j ==1:
                files[j] = glob.glob(f"ukf_results/ukf_agents_{num}_prop_{1}*") 
                #wierd special case with 1 and 1.0 discrepancy
            else:
                files[round(j,2)] = glob.glob(f"ukf_results/ukf_agents_{num}_prop_{round(j,2)}*")

        for k,_ in enumerate(files.keys()):
            o_L2_2=[]
            u_L2_2 = []
            for file in files[_]:
                f = open(file,"rb")
                u = pickle.load(f)
                f.close()
                pred,do,du = l2_parser(u,float(_))#
                "grand means"
                #o_L2_2.append(np.nanmean(do,axis=0))
                #u_L2_2.append(np.nanmean(du,axis=0))
                "grand medians"
                o_L2_2.append(np.nanmedian(do,axis=0))
                u_L2_2.append(np.nanmedian(du,axis=0))
        
            o_L2[i,k]=np.nanmean(np.hstack(o_L2_2))
            u_L2[i,k]=np.nanmean(np.hstack(u_L2_2))
            
    return o_L2,u_L2
    
def grand_L2_plot(data,n,prop,observed,save):
    """produces grand median matrix for all 30 ABM runs for choropleth plot
    
    Parameters
    ------
    data : array_like
        L2 `data` matrix from grand_L2_matrix
    n,prop : float
        population `n` and square size `prop`
    save : bool
        `save` plot?

    """ 
    
    data = np.rot90(data,k=1) #rotate frame 90 degrees so right way up for plots
    
    "initiate plot"
    f,ax=plt.subplots(figsize=(8,8))
    "colourmap"
    cmap = cm.viridis
    cmap.set_bad("white") #set nans for unobserved full prop to white
    
    data2 = np.ma.masked_where(np.isnan(data),data) #needed to get bad white squares in imshow
    data2=np.flip(data2,axis=0) #rotate so imshow right way up (origin bottom left)
    im=ax.imshow(data2,interpolation="nearest",cmap=cmap,origin="lower")
    
    "labelling"
    ax.set_xticks(np.arange(len(n)))
    ax.set_yticks(np.arange(len(prop)))
    ax.set_xticklabels(n)
    ax.set_yticklabels(prop)
    ax.set_xticks(np.arange(-.5,len(n),1),minor=True)
    ax.set_yticks(np.arange(-.5,len(prop),1),minor=True)
    ax.grid(which="minor",color="k",linestyle="-",linewidth=2)
    ax.set_xlabel("Number of Agents")
    ax.set_ylabel("Proportion of Agents Observed")
    #plt.title("Grand L2s Over Varying Agents and Percentage Observed")


    "labelling squares"
    data = np.flip(data,axis=0)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            plt.text(j,i,str(data[i,j].round(2)),ha="center",va="center",color="w",
                     path_effects=[pe.Stroke(linewidth = 0.4,foreground='k')])
            
    "colourbar alignment and labelling"
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("right",size="5%",pad=0.05)
    cbar=plt.colorbar(im,cax,cax)
    cbar.set_label("Grand Mean L2 Error")
    
    "further labelling and saving depending on observed/unobserved plot"
    if observed:
        cbar.set_label("Observed Median L2s")
        #ax.set_title("Observed Agent L2s")
        ax.set_ylabel("Proportion of Agents Observed (x100%)")
        if save:
            plt.savefig("Observed_Grand_L2s.pdf")

    else:
        cbar.set_label("Unobserved Median L2s")
        #ax.set_title("Unobserved Agent L2s")
        ax.set_ylabel("Proportion of Agents Observed (x100%)")
        if save:
            plt.savefig("Unobserved_Grand_L2s.pdf")
            
def boxplot_parser(n,prop):
    """similar to grand_L2_matrix but creats a pandas frame for sns.catplot to read
    
    .. deprecated:: 
        use median boxplots this is dumb
    
    Parameters
    ------
    n,prop : float
        population `n` and proportion `prop`
    
    Returns
    ------
    L2 : array_like
        `L2` matrix of grand medians. Produces data frame with columns for n,
        prop, and median. This version gives a median for every AGENT rather
        than a grand median for each run (I.E 30x12xpopulations rows vs 30x12 rows)
    

    """    
    observed = {}
    unobserved ={}
    for i,num in enumerate(n):
        files={}
        for j in prop:
            if j ==1:
                files[j] = glob.glob(f"ukf_results/ukf_agents_{num}_prop_{1}*") 
                #wierd special case with 1 and 1.0 discrepancy
            else:
                files[round(j,2)] = glob.glob(f"ukf_results/ukf_agents_{num}_prop_{round(j,2)}*")
        observed[num] = {}
        unobserved[num] = {}
        for _ in files.keys():
            o_L2_2=[]
            u_L2_2 = []
            for file in files[_]:
                f = open(file,"rb")
                u = pickle.load(f)
                f.close()
                pred,do,du = l2_parser(u,float(_))#
                
                o_L2_2.append(np.apply_along_axis(np.nanmean,0,do))
                u_L2_2.append(np.apply_along_axis(np.nanmean,0,du))
            observed[num][_] = np.hstack(o_L2_2)
            unobserved[num][_] = np.hstack(u_L2_2)
          
    "stack dictionaries into dataframe with corresponding n and prop next to each agent error"
    obs_sub_frames = []
    uobs_sub_frames = []
    
    for i in n:
        for j in prop:
            obs = observed[i][j]
            uobs = unobserved[i][j]
            obs_sub_frames.append(pd.DataFrame([[i]*len(obs),[j]*len(obs),obs]).T)
            uobs_sub_frames.append(pd.DataFrame([[i]*len(uobs),[j]*len(uobs),uobs]).T)

    "stack into grand frames and label columns"
    obs_frame = pd.concat(obs_sub_frames)
    obs_frame.columns = ["n","proportion observed (x100%)","observed L2 agent errors"]
    uobs_frame = pd.concat(uobs_sub_frames)
    uobs_frame.columns = ["n","proportion observed (x100%)","unobserved L2 agent errors"]

    
    return obs_frame ,uobs_frame

def boxplot_plots(n,prop,frame,separate,observed,save):  
    """produces grand median boxplot for all 30 ABM runs for choropleth plot
    
    ..deprecated:: 
        use medians below
    Parameters
    ------
    frame : array_like
        L2 `data` matrix from grand_L2_matrix
    n,prop : float
        population `n` and proportion 'prop'
    save,seperate : bool
        `save` plot?
        `seperate` box plots by population or have one big catplot?

    """    
    if separate:
        for i in n:
            if observed:
                f_name = f"Observed_boxplot_{i}.pdf"
                y_name = "observed L2 agent errors"
    
            else:
                y_name = "unobserved L2 agent errors"
                f_name = f"Unobserved_boxplot_{i}.pdf"
                
            n_subframe = frame.loc[frame["n"]==str(i)]
    
            f = plt.figure()
            sns.boxplot(x="proportion observed (x100%)",y=y_name,data=n_subframe)
            if save:
                f.savefig(f_name)
    
    else:
        if observed:
            f_name = f"Observed_boxplot.pdf"
            y_name = "observed L2 agent errors"

        else:
            y_name = "unobserved L2 agent errors"
            f_name = f"Unobserved_boxplot.pdf"

        f = plt.figure()
        sns.catplot(x="proportion observed (x100%)",y=y_name,col="n",kind="box", data=frame)
        plt.tight_layout()
        if save:
            plt.savefig(f_name)
 
    
def boxplot_medians(n,prop):
    """similar to grand_L2_matrix but creats a pandas frame for sns.catplot to read
    
    .. deprecated:: 
        use median boxplots this is dumb
    
    Parameters
    ------
    n,prop : float
        population `n` and proportion `prop`
    
    Returns
    ------
    L2 : array_like
        `L2` matrix of grand medians. Produces data frame with columns for n,
        prop, and median. This version gives a median for every AGENT rather
        than a grand median for each run (I.E 30x12xpopulations rows vs 30x12 rows)
    

    """    
    observed = {}
    unobserved ={}
    for i,num in enumerate(n):
        files={}
        for j in prop:
            if j ==1:
                files[j] = glob.glob(f"ukf_results/ukf_agents_{num}_prop_{1}*") 
                #wierd special case with 1 and 1.0 discrepancy
            else:
                files[round(j,2)] = glob.glob(f"ukf_results/ukf_agents_{num}_prop_{round(j,2)}*")
        observed[num] = {}
        unobserved[num] = {}
        for _ in files.keys():
            o_L2_2=[]
            u_L2_2 = []
            for file in files[_]:
                f = open(file,"rb")
                u = pickle.load(f)
                f.close()
                pred,do,du = l2_parser(u,float(_))#
                
                o_L2_2.append(np.nanmean(np.nanmedian(do,axis=0)))
                u_L2_2.append(np.nanmean(np.nanmedian(du,axis=0)))
            observed[num][_] = np.hstack(o_L2_2)
            unobserved[num][_] = np.hstack(u_L2_2)
          
    "stack dictionaries into dataframe with corresponding n and prop next to each agent error"
    obs_sub_frames = []
    uobs_sub_frames = []
    
    for i in n:
        for j in prop:
            obs = observed[i][j]
            uobs = unobserved[i][j]
            obs_sub_frames.append(pd.DataFrame([[i]*len(obs),[j]*len(obs),obs]).T)
            uobs_sub_frames.append(pd.DataFrame([[i]*len(uobs),[j]*len(uobs),uobs]).T)

    "stack into grand frames and label columns"
    obs_frame = pd.concat(obs_sub_frames)
    obs_frame.columns = ["n","proportion observed (x100%)","observed L2 agent errors"]
    uobs_frame = pd.concat(uobs_sub_frames)
    uobs_frame.columns = ["n","proportion observed (x100%)","unobserved L2 agent errors"]

    
    return obs_frame ,uobs_frame

def median_boxplot(n,prop,frame,separate,observed,save):
    """produces grand median boxplot for all 30 ABM runs for choropleth plot
    
   
    Parameters
    ------
    frame : array_like
        L2 `data` matrix from grand_L2_matrix
    
    save,observed : bool
        `save` plot?
        `seperate` box plots by population or have one big catplot?

    """       
    if separate:
        for i in n:
            if observed:
                f_name = f"Observed_boxplot_{i}.pdf"
                y_name = "observed L2 agent errors"
    
            else:
                y_name = "unobserved L2 agent errors"
                f_name = f"Unobserved_boxplot_{i}.pdf"
                
            n_subframe = frame.loc[frame["n"]==str(i)]
    
            f = plt.figure()
            sns.boxplot(x="proportion observed (x100%)",y=y_name,data=n_subframe)
            if save:
                f.savefig(f_name)
    
    else:
        if observed:
            f_name = f"MEdian_Observed_boxplot.pdf"
            y_name = "observed L2 agent errors"

        else:
            y_name = "unobserved L2 agent errors"
            f_name = f"Median Unobserved_boxplot.pdf"

        f = plt.figure()
        sns.catplot(x="proportion observed (x100%)",y=y_name,col="n",kind="box", data=frame)
        plt.tight_layout()
        if save:
            plt.savefig(f_name)
    
#%% 
if __name__ == "__main__":
    
    """
    plot1 - plot choropleth results
    plot2 - plot all agent median boxplots
    plot3 - per run grand median boxplots
    n - populations
    prop - proportions observed
    """
    plot1 = False
    plot2 = False
    plot3 = True
    n= [10,20,30]
    prop = [0.25,0.5,0.75,1.0]
    
    save=True
    if plot1:
        O,U = grand_L2_matrix(n,prop)
        grand_L2_plot(O,n,prop,True,save)
        grand_L2_plot(U,n,prop,False,save)
    if plot2:
        obs_frame ,uobs_frame = boxplot_parser(n,prop)
        boxplot_plots(n,prop,obs_frame,False,True,save)        
        boxplot_plots(n,prop,uobs_frame,False,False,save)
    if plot3:
        obs_frame,uobs_frame= boxplot_medians(n,prop)
        median_boxplot(n,prop,obs_frame,False,True,save)        
        median_boxplot(n,prop,uobs_frame,False,False,save)
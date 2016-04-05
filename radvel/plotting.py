import pylab as pl
from mpl_toolkits.axes_grid.anchored_artists import AnchoredText
from mpl_toolkits.axes_grid1 import make_axes_locatable,AxesGrid
from matplotlib.ticker import NullFormatter
import radvel
from radvel.utils import t_to_phase, fastbin
from astropy.time import Time
import string
from matplotlib import rcParams
import numpy as np
import matplotlib
import corner

rcParams['font.size'] = 24

telfmts = {'j': 'ko', 'k': 'ks', 'a': 'gd', 'h': 'gs',
           'hires_rj': 'ko', 'hires_rk': 'ks', 'apf': 'gd', 'harps': 'gs'}
teldecode = {'a': 'APF', 'k': 'HIRES_k', 'j': 'HIRES_j'}
msize = 7
elinecolor = '0.6'

    
def _mtelplot(x, y, e, tel, ax, telfmts):
        utel = np.unique(tel)
        for t in utel:
            xt = x[tel == t]
            yt = y[tel == t]
            et = e[tel == t]
            if t == '': t = 'j'
            if t == 'j' or t == 'k':
                ax.errorbar(xt,yt,yerr=et,fmt=telfmts[t], ecolor=elinecolor, markersize=msize, capsize=0, markeredgecolor=telfmts[t][0], markerfacecolor='none',
                            markeredgewidth=2)
            elif t not in telfmts.keys():
                ax.errorbar(xt,yt,yerr=et,fmt='o', ecolor=elinecolor, markersize=msize, capsize=0, markeredgewidth=0)
            else:
                ax.errorbar(xt,yt,yerr=et,fmt=telfmts[t], ecolor=elinecolor, markersize=msize, capsize=0, markeredgecolor=telfmts[t][0], markerfacecolor=telfmts[t][0],
                            markeredgewidth=3)

        ax.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter(useOffset=False))
        ax.xaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter(useOffset=False))

def rv_multipanel_plot(post, saveplot=None, **kwargs):
    """
    Multi-panel RV plot to display model using post.params orbital paramters.

    :param post: Radvel posterior object. The model plotted will be generated from post.params
    :type post: radvel.Posterior

    :param saveplot: (optional) Name of output file, will show as interactive matplotlib window if not defined.
    :type string:
    
    :param nobin: (optional) If True do not show binned data on phase plots
    :type nobin: bool
    
    :param yscale_auto: (optional) Use matplotlib auto y-axis scaling
    :type yscale_auto: bool
    
    :param yscale_sigma: (optional) Scale y-axis limits to be +/- yscale_sigma*(RMS of data plotted)
    :type yscale_sigma: float
    
    :param telfmts: (optional) dictionary mapping instrument code to plotting format code
    :type telfmts: dict
    
    :param nophase: (optional) omit phase-folded plots
    :type nophase: bool
        
    """

    nobin = kwargs.pop('nobin', False)
    yscale_sigma = kwargs.pop('yscale_sigma', 3.0)
    yscale_auto = kwargs.pop('yscale_auto', False)
    telfmts = kwargs.pop('telfmts', globals()['telfmts'])
    nophase = kwargs.pop('nophase', False)
    
    if saveplot != None: resolution = 1e4
    else: resolution = 2000

    cpsparams = post.params.basis.to_cps(post.params)
    model = post.likelihood.model
    rvtimes = post.likelihood.x
    rvdat = post.likelihood.y
    rverr = post.likelihood.yerr
    n = model.num_planets
    e = 2450000

    if isinstance(post.likelihood, radvel.likelihood.CompositeLikelihood):
        like_list = post.likelihood.like_list
    else:
        like_list = [ post.likelihood ]
    
    periods = []
    for i in range(model.num_planets):
        periods.append(cpsparams['per%d' % (i+1)])
    longp = max(periods)
    shortp = min(periods)
        
    dt = max(rvtimes)-min(rvtimes)
    rvmodt = np.linspace(min(rvtimes)-0.05*dt,max(rvtimes)+0.05*dt+longp,resolution)

    rvmod2 = model(rvmodt)
    rvmod = model(rvtimes)

    rawresid = post.likelihood.residuals()
    resid = rawresid + cpsparams['dvdt']*(rvtimes-model.time_base) + cpsparams['curv']*(rvtimes-model.time_base)**2
    slope = cpsparams['dvdt']*(rvmodt-model.time_base) + cpsparams['curv']*(rvmodt-model.time_base)**2
    slope_low = cpsparams['dvdt']*(rvtimes-model.time_base) + cpsparams['curv']*(rvtimes-model.time_base)**2

    if nophase: fig = pl.figure(figsize=(19.0,23.0))
    elif n == 1: fig = pl.figure(figsize=(19.0,16.0))
    else: fig = pl.figure(figsize=(19.0,16.0+4*n))        
    rect = [0.07, 0.64, 0.865, 1./(n+1)-0.02]
    axRV = pl.axes(rect)
    pl.subplots_adjust(left=0.1,top=0.865,right=0.95)
    plotindex = 1
    pltletter = ord('a')
    ax = axRV
    
    #Unphased plot
    ax.axhline(0, color='0.5', linestyle='--', lw=2)
    ax.plot(rvmodt-e,rvmod2,'b-',linewidth=1, rasterized=False)
    ax.annotate("%s)" % chr(pltletter), xy=(0.01,0.85), xycoords='axes fraction', fontsize=28, fontweight='bold')
    pltletter += 1
    _mtelplot(rvtimes-e,rawresid+rvmod,rverr,post.likelihood.telvec, ax, telfmts)
    ax.set_xlim(min(rvtimes-e)-0.01*dt,max(rvtimes-e)+0.01*dt)
    
    pl.setp(axRV.get_xticklabels(), visible=False)

    # Years on upper axis
    axyrs = axRV.twiny()
    axyrs.set_xlim(min(rvtimes-e)-0.01*dt,max(rvtimes-e)+0.01*dt)
    #yrticklocs = [date2jd(datetime(y, 1, 1, 0, 0, 0))-e for y in [1998, 2002, 2006, 2010, 2014]]
    yrticklocs = []
    yrticklabels = []
    for y in [1988,1992,1996,2000,2004,2008,2012,2016]:
        jd = Time("%d-01-01T00:00:00" % y, format='isot', scale='utc').jd - e
        if jd > ax.get_xlim()[0] and jd < ax.get_xlim()[1]:
            yrticklocs.append(jd)
            yrticklabels.append("%d" % y)
    axyrs.set_xticks(yrticklocs)
    axyrs.set_xticklabels(yrticklabels)    
    if len(yrticklabels) > 0:
        pl.xlabel('Year')
        axyrs.grid(False)

    if not yscale_auto: ax.set_ylim(-yscale_sigma*np.std(rawresid+rvmod), yscale_sigma*np.std(rawresid+rvmod))
    ax.set_ylabel('RV [m s$^{-1}$]')
    ticks = ax.yaxis.get_majorticklocs()
    ax.yaxis.set_ticks(ticks[1:])

    divider = make_axes_locatable(axRV)
    axResid = divider.append_axes("bottom",size="50%",pad=0.0,sharex=axRV,sharey=None)
    ax = axResid

    #Residuals
    ax.plot(rvmodt-e,slope,'b-',linewidth=3)
    ax.annotate("%s)" % chr(pltletter), xy=(0.01,0.80), xycoords='axes fraction', fontsize=28, fontweight='bold')
    pltletter += 1

    _mtelplot(rvtimes-e,resid,rverr, post.likelihood.telvec,ax, telfmts)
    if not yscale_auto: ax.set_ylim(-yscale_sigma*np.std(resid), yscale_sigma*np.std(resid))
    ax.set_xlim(min(rvtimes-e)-0.01*dt,max(rvtimes-e)+0.01*dt)
    ticks = ax.yaxis.get_majorticklocs()
    ax.yaxis.set_ticks([ticks[0],0.0,ticks[-1]])
    xticks = ax.xaxis.get_majorticklocs()
    pl.xlabel('BJD$_{\\mathrm{TDB}}$ - %d' % e)
    ax.set_ylabel('Residuals')

    
    # Define the locations for the axes
    axbounds = ax.get_position().bounds
    bottom = axbounds[1]
    height = (bottom - 0.10) / n
    textloc = bottom / 2
    bottom -= height + 0.05
    left, width = 0.07, 0.75

    
    #Phase plots
    for i in range(n):
        if nophase: break
        
        pnum = i+1
        #print "Planet %d" % pnum

        rvdat = rvdat.copy()

        rvmod2 = model(rvmodt, planet_num=pnum) - slope
        
        modph = t_to_phase(post.params, rvmodt, pnum, cat=True) - 1

        rvdat = rawresid + model(rvtimes, planet_num=pnum) - slope_low
        
        phase = t_to_phase(post.params, rvtimes, pnum, cat=True) - 1
        p2 = t_to_phase(post.params, rvtimes, pnum, cat=False) - 1

        rvdatcat = np.concatenate((rvdat,rvdat))
        rverrcat = np.concatenate((rverr,rverr))
        rvmod2cat = np.concatenate((rvmod2,rvmod2))

        bint, bindat, binerr = fastbin(phase+1, rvdatcat, nbins=25)
        bint -= 1.0

        rect = [left, bottom-(i)*height, (left+width)+0.045, height]
        if n == 1: rect[1] -= 0.03
        ax = pl.axes(rect)

        ax.axhline(0, color='0.5', linestyle='--', lw=2)
        ax.plot(sorted(modph),rvmod2cat[np.argsort(modph)],'b-',linewidth=3)
        ax.annotate("%s)" % chr(pltletter), xy=(0.01,0.85), xycoords='axes fraction', fontsize=28, fontweight='bold')
        pltletter += 1

        _mtelplot(phase,rvdatcat,rverrcat, np.concatenate((post.likelihood.telvec,post.likelihood.telvec)), ax, telfmts)
        if not nobin and len(rvdat) > 10: ax.errorbar(bint,bindat,yerr=binerr,fmt='ro', ecolor='r', markersize=msize*2.5, markeredgecolor='w', markeredgewidth=2)

        pl.xlim(-0.5,0.5)
        #meanlim = np.mean([-min(rvdat), max(rvdat)])
        #meanlim += 0.10*meanlim
        #pl.ylim(-meanlim, meanlim)
        if not yscale_auto: pl.ylim(-yscale_sigma*np.std(rvdatcat), yscale_sigma*np.std(rvdatcat))
        
        letters = string.lowercase
        planetletter = letters[i+1]
        labels = ['$P_{\\rm %s}$' % planetletter,'$K_{\\rm %s}$' % planetletter,'$e_{\\rm %s}$' % planetletter]
        units = ['days','m s$^{-1}$','']
        indicies = [0,4,2,2]
        spacing = 0.09
        xstart = 0.65
        ystart = 0.89
        
        if i < n-1:
            ticks = ax.yaxis.get_majorticklocs()
            ax.yaxis.set_ticks(ticks[1:-1])

        if n > 1: fig.text(0.01,textloc,'RV [m s$^{-1}$]',rotation='vertical',ha='center',va='center',fontsize=28)
        else: pl.ylabel('RV [m s$^{-1}$]')
        pl.xlabel('Phase')

        print_params = ['per', 'k', 'e']
        for l,p in enumerate(print_params):
            txt = ax.annotate('%s = %4.2f %s' % (labels[l],cpsparams["%s%d" % (print_params[l],pnum)] ,units[l]),(xstart,ystart-l*spacing),
                                    xycoords='axes fraction', fontsize=28)
        

    if saveplot != None:
        pl.savefig(saveplot,dpi=150)
        print "RV multi-panel plot saved to %s" % saveplot
    else: pl.show()

def corner_plot(post, chains, saveplot=None):
    """
    Make a corner plot from the output MCMC chains and a posterior object.

    :param post: Radvel posterior object
    :type post: radvel.Posterior

    :param chains: MCMC chains output by radvel.mcmc
    :type chains: pandas.DataFrame
    
    :param saveplot: (optional) Name of output file, will show as interactive matplotlib window if not defined.
    :type string:
    
    """

    
    labels = [k for k in post.vary.keys() if post.vary[k]]

    f = rcParams['font.size']
    rcParams['font.size'] = 12
    
    fig = corner.corner(chains[labels],
                        labels=labels,
                        label_kwargs={"fontsize": 14},
                        plot_datapoints=False,
                        bins=20,
                        quantiles=[.16,.5,.84],
                        show_titles = True,
                        title_kwargs={"fontsize": 14})
    
    if saveplot != None:
        pl.savefig(saveplot,dpi=150)
        print "Corner plot saved to %s" % saveplot
    else: pl.show()

    rcParams['font.size'] = f
    

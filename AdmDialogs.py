# The Admin4 Project
# (c) 2013-2014 Andreas Pflug
#
# Licensed under the Apache License, 
# see LICENSE.TXT for conditions of usage

import adm
import logger
import sys, os, zipfile
import wx
from wh import xlt, copytree
import version

class PasswordDlg(adm.Dialog):
  def __init__(self, parentWin, msg, caption):
    adm.Dialog.__init__(self, parentWin)
    self.SetTitle(caption)
    self.staticPassword=msg

  def Save(self):
    return True

class AboutDlg(adm.Dialog):
  def __init__(self, parent):
    super(AboutDlg, self).__init__(parent)
    stdFont=self.GetFont()
    pt=stdFont.GetPointSize()
    family=stdFont.GetFamily()
    bigFont=wx.Font(pt*2 , family, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
    mediumFont=wx.Font(pt*1.4, family, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD)
    self['Admin'].SetFont(bigFont)
    self['Version'].SetFont(mediumFont)

    self.Admin="Admin4"
    self.Version=xlt("Version %s") % version.version

    if not hasattr(sys, "frozen"):
        self.Revision = xlt("(%s)\nunknown changes") % version.revDate 
        rev=xlt("unknown")
    elif version.revLocalChange:
      if version.revDirty:
        self.Revision = xlt("(+ %s)\nLocally changed/uncommitted") % version.modDate 
        rev=xlt("locally changed %s") % version.modDate
      else:
        self.Revision = xlt("(+ %s)\nLocally committed") % version.revDate 
        rev="+ %s" % version.revDate
    elif version.revOriginChange:
      self.Revision = "(+ %s)" % version.revDate
      rev="+ %s" % version.revDate 
    else:
      if version.tagDate:
        self.Revision = "(%s)" % version.tagDate
      rev=version.tagDate 
    self.Description = version.description
    copyrights=[version.copyright]
    licenses=[xlt("%s\nFor details see LICENSE.TXT") % version.license]

    lv=self['Modules']
    lv.AddColumn(xlt("Module"), "PostgreSQL")
    lv.AddColumn(xlt("Ver."), "2.4.5")
    lv.AddColumn(xlt("Rev."), "2014-01-01++")
    lv.AddColumn(xlt("Description"), 30)
    
    vals=["Core", version.version, rev, xlt("Admin4 core framework")]
    lv.AppendItem(adm.images.GetId("Admin4Small"), vals)

    wxver=wx.version().split(' ')
    v=wxver[0].split('.')
    vals=["wxWidgets", '.'.join(v[:3]), '.'.join(v[3:]), "wxWidgets %s" % ' '.join(wxver[1:])]
    lv.AppendItem(adm.images.GetId("wxWidgets"), vals)

    for modid, mod in adm.modules.items():
      vals=[]
      mi=mod.moduleinfo
      modulename=mi.get('modulename', modid)
      vals.append(modulename)
      vals.append(mi.get('version'))
      rev=mi.get('revision')
      if rev:
        vals.append(rev)
      else:
        vals.append("")
      vals.append(mi.get('description'))
      serverclass=mi['serverclass'].__name__.split('.')[-1]
      icon=adm.images.GetId(os.path.join(modid, serverclass))
      lv.AppendItem(icon, vals)
      credits=mi.get('credits')
      if credits:
        copyrights.append(credits)
      license=mi.get("license")
      if license:
        licenses.append("%s: %s" % (modulename, license))
    self.Copyright = "\n\n".join(copyrights).replace("(c)", unichr(169))
    
    licenses.append("Additional licenses from libraries used may apply.")
    self.License="\n\n".join(licenses)
  

class PreferencesDlg(adm.CheckedDialog):
  def __init__(self, parentWin):
    adm.Dialog.__init__(self, parentWin)
    self.panels=[]

    notebook=self['Notebook']
    for panelclass in adm.getAllPreferencePanelClasses():
        panel=panelclass(self, notebook)
        self.panels.append(panel)
        notebook.AddPage(panel, panel.name)

  def Go(self):
    for panel in self.panels:
      panel.Go()
      panel.SetUnchanged()

  def GetChanged(self):
    for panel in self.panels:
      if panel.GetChanged():
        return True
    return False

  def Check(self):
    for panel in self.panels:
      if hasattr(panel, "Check"):
        if not panel.Check():
          return False
    return True

  def Save(self):
    for panel in self.panels:
      if not panel.Save():
        return False
    return True


class UpdateDlg(adm.Dialog):
  def __init__(self, parentWin):
    adm.Dialog.__init__(self, parentWin)
    self.Bind("Target")
    self.Bind("Search", self.OnSearch)
    self.SetTitle(xlt("Update %s modules") % adm.appTitle)
    
  def Go(self):
    if not os.access(adm.loaddir, os.W_OK):
      self.EnableControls("Target Search Ok", False)
      self.ModuleInfo=xlt("Update not possible:\nProgram directory cannot be written.")
    else:
      self.Check()
 
  def OnSearch(self, evt):
    dlg=wx.FileDialog(self, xlt("Select Update dir or zip"), wildcard="Module ZIP (*.zip)|*.zip|Module (*.py)|*.py", style=wx.FD_CHANGE_DIR|wx.FD_FILE_MUST_EXIST|wx.FD_OPEN)
    if dlg.ShowModal() == wx.ID_OK:
      path=dlg.GetPath()
      if path.endswith('.py'):
        path = os.path.dirname(path)
      self.Target=path
      self.OnCheck()
    
  def Check(self):
    modSrc=None
    canInstall=True
    self.ModuleInfo = xlt("Please select module update ZIP file or directory.")

    fnp=os.path.basename(self.target).split('-')
    self.modid=fnp[0]
    if os.path.isdir(self.Target):
      initMod=os.path.join(self.Target, "__init__.py")
      if os.path.exists(initMod):
        try:
          f=open(initMod, "r")
          modSrc=f.read()
          f.close
        except:
          pass
    elif self.Target.lower().endswith(".zip") and os.path.exists(self.Target) and zipfile.is_zipfile(self.Target):
      if len(fnp) < 2:
        logger.debug("Not an update zip: %s", self.Target)
        return False
      try:
        zip=zipfile.ZipFile(self.Target)
        modnameSlash=self.modid+os.path.sep
        for f in zip.namelist():
          if not f.startswith(modnameSlash):
            logger.debug("Update zip %s contains additional non-module data", self.Target)
            return False
        f=zip.open("%s__init__.py" % modnameSlash)
        modSrc=f.read()
        zip.close()
        
      except Exception as _e:
        logger.exception("Error while reading moduleinfo from zip %s", self.Target)
        pass

    if modSrc:
      moduleinfo=None
      try:
        sys.skipSetupInit=True
        exec modSrc
      except Exception as _e:
        logger.exception("Error executing code in %s", self.Target)
      finally:
        del sys.skipSetupInit
          
      if moduleinfo:
        try:
          self.modname=moduleinfo['modulename']
          revision= moduleinfo.get('revision')
          msg=[ xlt("Module %s : %s") % (self.modname, moduleinfo['description']), "" ]
          
          if revision:
            delta=""
            installed=adm.modules.get(self.modid)
            if installed:
              instrev=installed.moduleinfo.get('revision')
              if instrev:
                if instrev == revision:
                  delta = xlt(" - already installed")
                elif instrev > revision:
                  delta=xlt(" - %s already installed" % instrev)
              else:
                delta=xlt(" - can't check installed")

              msg.append(xlt("Version %s Revision %s%s") % (moduleinfo['version'], revision, delta))
          else:
            msg.append(xlt("Version %s Revision unknown") % moduleinfo['version'])

          rqVer=moduleinfo['requiredAdmVersion']
          msg.append("")
          if moduleinfo['requiredAdmVersion'] > version.version:
            msg.append(xlt("Module requires Admin4 Core version %s") % rqVer)
            canInstall=False
          else:
            testedVer=moduleinfo.get('testedAdmVersion')
            if testedVer and testedVer < version.version:
              msg.append(xlt("not verified with this Admin4 Core version"))
        except Exception as _e:
          logger.exception("Format error of %s moduleinfo", self.Target)
          return False
        
        self.ModuleInfo="\n".join(msg)
        return canInstall

    return False

  
  
  def Execute(self):
    if os.path.isdir(self.Target):
      dst=os.path.join(adm.loaddir, self.modid)
      try:
        os.mkdir(dst)
      except:
        pass
      copytree(self.Target, dst)
    else:
      try:
        zip=zipfile.ZipFile(self.Target)
        zip.extractall(adm.loaddir)
        zip.close()
      except Exception as _e:
        logger.exception("Error extracting %s", self.Target)
        return False
    
    dlg=wx.MessageDialog(self, xlt("New module requires program restart.\nExit now?"), 
                         xlt("Installed new module %s") % self.modname,
                         wx.YES_NO|wx.NO_DEFAULT)
    if dlg.ShowModal() == wx.ID_YES:
      sys.exit()
    return True
 
  
  
class Preferences(adm.NotebookPanel):
  name="General"
  
  def Go(self):
    self.ConfirmDeletes=adm.confirmDeletes

  def Save(self):
    adm.confirmDeletes=self.ConfirmDeletes
    adm.config.Write("ConfirmDeletes", adm.confirmDeletes)
    return True

  @staticmethod
  def Init():
    adm.confirmDeletes=adm.config.Read("ConfirmDeletes", True)


  
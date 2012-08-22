# cygwin-get - The Cygwin Package Manager

----
## ABOUT
cygwin-get is cygwin package manager based of CLI.  
It can resolve packages dependencies and download it.  
cygwin-get only running on windows.

* Author : Zealic


----
## DOCUMENTATION
### How to use ?
* Download packages  
  `cygwin-get.py vim`
* Resolve packages dependencies (Do not download)  
  `cygwin-get.py -n vim`
* Download packages with mirror  
  `cygwin-get.py -m http://www.netgull.com/cygwin/ vim`
* Download specified version packages  
  `cygwin-get.py -v prev vim`
* Download packages to specified directory  
  `cygwin-get.py -d D:\my_cyg_packages vim`
* Through specified response file to download package  
  `cygwin-get.py -r pkg.xml`

_pkg.xml_ file content:
```xml
<?xml version="1.0" ?>
<cygwin>
  <!-- Basic -->
  <package name="@Admin" /> <!-- category -->
  <package name="@Base" /> <!-- category -->
  <package name="@Archive" /> <!-- category -->
  <package name="cygport" />
  <!-- Editors -->
  <package name="emacs" />
  <package name="nano" />
  <package name="vim" />
  <!-- Languages -->
  <package name="perl" />
  <package name="perl-libwin32" />
  <package name="python" />
  <package name="ruby" />
  <!-- Version Control System -->
  <package name="subversion" />
  <package name="git" />
  <package name="git-svn" />
</cygwin>
```

---
# Links
* Home page: http://github.com/zealic/cygwin-get/


----
## FEEDBACK
Please submit feedback via the cygwin-get tracker:  
http://github.com/zealic/cygwin-get/issues


LICENSE
---
[BSD License](http://en.wikipedia.org/wiki/BSD_license)


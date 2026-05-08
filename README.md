WUSTL ESPM Electron Probe MicroAnalyzer Web Tool for basic data explortation.

The purpose of this site is to take excel data straight from the micro probe and with some small additions(pair_id and phase type) a given user can begin to compile raw data straight from the probe. 

The original publication of this site is May 2026 by Tomás Salazar. 

HOW DOES THE SITE WORK:
This site was created using python language(python3) and dash app.

The MAIN.py file is the heart of the website that handles the bringing in of all the pages. This is also the home screen. 
The requirements.txt file contains all of the necessary modules that python(pip) needs to download in order to work and manipulate directly on the local server before pushing to render.com to publish to the public web. 
The assisstantfiles folder is where all of the additional python files and images lives. 

Keep the _pychache_ the way that it is. 
The Pages folder holds all of the different pages for the site(ie. info, PARTITION ANALYSIS, BULK ANALYSIS, SHIVELUCH) and this is just for the format on the pages of the site. The real analysis and plotting happens in the assistant files that correspond to the data. 

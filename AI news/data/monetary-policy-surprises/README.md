# Monetary Policy Surprises

The code in the R script `mps.R` calculates monetary policy surprises from data in the
U.S. Monetary Policy Event-Study Database (USMPD).

Source: https://sffed.us/usmpd

## Instructions

1. Download latest version of `USMPD.xlsx` from https://sffed.us/usmpd
2. Open R session and set working directory to folder with `mps.R`
   -> This folder should contain `USMPD.xlsx`
3. Ensure all required R packages are installed, for example using the command
   `install.packages(c("readxl", "dplyr", "lubridate", "readr"))`
4. Run script mps.R, for example using the command
   `source("mps.R")`

## Output

The code writes two separate CSV files, which contain monetary policy surprises constructed with the
methodology of Acosta et al. (2025). The *units* of the underlying high-frequency money market futures
rate changes, as well as the daily one-year Treasury yield changes, are percentage points. The surprises are
normalized so that they have a one-for-one impact on the one-year Treasury yield.

`mps.csv` contains three different surprises, for the statements (STMT), press conferences (PC) and monetary
events (ME) after FOMC meetings.

`mps_minutes.csv` contains the surprises for releases of the FOMC meeting minutes.


## Reference

Please cite as:

Acosta, Miguel, Andrea Ajello, Michael Bauer, Francesca Loria, and Silvia Miranda-Agrippino, 2025, "Financial Market Effects of FOMC Communication: Evidence from a New Event-Study Database," Federal Reserve Bank of San Francisco Working Paper 2025-30.


## Contact

For questions or feedback, contact the SF Fed's Center for Monetary Research at <mailto:cmr@sf.frb.org>.
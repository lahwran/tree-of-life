import ceylon.time { Duration }

Integer msseconds = 1000 * 60;
Integer mshours = msseconds * 60;
Duration idealFocusTime = Duration(25 * msseconds);
Duration scheduleLength = Duration(mshours * 24 * 7);

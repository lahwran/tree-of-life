import ceylon.time { Duration }

Integer msminutes = 1000 * 60;
Integer mshours = msminutes * 60;
Duration idealFocusTime = Duration(25 * msminutes);
Duration scheduleLength = Duration(mshours * 24 * 7);
Integer crossoverCount = 5;

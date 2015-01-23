import ceylon.time { Duration }

Integer msminutes = 1000 * 60;
Integer mshours = msminutes * 60;
Duration idealFocusTime = Duration(25 * msminutes);
Duration scheduleLength = Duration(mshours * 24 * 7);

// metaoptimize these:

Integer crossoverCount = 5;

Float addMax = 10.0;
Float addCurveExponent = 3.0;
Float delMax = 10.0;
Float delCurveExponent = 3.0;

import android.util { Log { logDebug = d } }
import com.google.gson { Gson }
import treeoflife.android { R { id { action_settings } } }

void testthing() {
    logDebug("thing.ceylon", "yay it worked!");
    Gson thing = Gson();
    logDebug("thing.ceylon", thing.toJson(1));

    logDebug("thing.ceylon", "action_settings id: ``action_settings``");
}

import android.util { Log { logDebug = d } }
import treeoflife.android { R }

import android.app { Activity }
import android.os { Bundle }
import android.view { Menu, MenuItem }


shared class MainActivity() extends Activity() {
    shared actual void onCreate(Bundle? savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        testthing();
    }


    shared actual Boolean onCreateOptionsMenu(Menu? menu) {

        // Inflate the menu; this adds items to the action bar if it is present.
        menuInflater.inflate(R.menu.main, menu);
        return true;
    }

    shared actual Boolean onOptionsItemSelected(MenuItem? item) {
        assert (exists item);
        // Handle action bar item clicks here. The action bar will
        // automatically handle clicks on the Home/Up button, so long
        // as you specify a parent activity in AndroidManifest.xml.
        Integer id = item.itemId;
        if (id == R.id.action_settings) {
            return true;
        }
        return super.onOptionsItemSelected(item);
    }

}


void testthing() {
    logDebug("thing.ceylon", "yay it worked!");
    logDebug("thing.ceylon", "action_settings id: ``R.id.action_settings``");
}




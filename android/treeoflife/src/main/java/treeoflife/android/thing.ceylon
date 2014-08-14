import android.util { Log }
import treeoflife.android { R }

import java.lang { ObjectArray, JavaString=String }

import android.app { Activity }
import android.os { Bundle }
import android.view { Menu, MenuItem }
import android.content.res { AssetManager }

String logtag = "thing.ceylon";

shared class MainActivity() extends Activity() {
    shared actual void onCreate(Bundle? savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        testthing();
        //AssetManager assetManager = this.assets;

        ObjectArray<JavaString> assets = Derp.derp(); //assetManager.list("");
        for (asset in assets.iterable) {
            Log.d(logtag, "Asset: ``asset else "null"``");
        }
    }


    shared actual Boolean onCreateOptionsMenu(Menu menu) {

        // Inflate the menu; this adds items to the action bar if it is present.
        menuInflater.inflate(R.menu.main, menu);
        return true;
    }

    shared actual Boolean onOptionsItemSelected(MenuItem item) {
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
    Log.d(logtag, "yay it worked!");
    Log.d(logtag, "action_settings id: ``R.id.action_settings``");
}




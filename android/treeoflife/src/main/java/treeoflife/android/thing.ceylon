import treeoflife.android { R }
import treeoflife.optimize { optimizeRun = run }

import java.lang {
    ObjectArray, JavaString=String, ByteArray, Runtime, System, Process
}
import java.io {
    BufferedReader, InputStreamReader, InputStream, OutputStream,
    FileOutputStream, File
}
import java.util {
    HashMap, Map, Arrays
}

import android.app { Activity }
import android.os { Bundle, Debug }
import android.util { Log }
import android.view { Menu, MenuItem, View }
import android.content.res { AssetManager }
import android.content { Context }

import android.text { TextUtils { strjoin = join } }

String logtag = "thing.ceylon";

BufferedReader makereader(InputStream stream) {
    return BufferedReader(InputStreamReader(stream));
}
void copystream(InputStream ins, OutputStream outs, Integer bufsize=1024) {
    value buf = ByteArray(bufsize);
    while (true) {
        value count = ins.read(buf);
        if (count == -1) {
            break;
        }
        outs.write(buf, 0, count);
    }
}

ObjectArray<JavaString> toJavaStrings(Iterable<String> strings) {
    value args = ObjectArray<JavaString>(strings.size);
    for (index -> string in strings.indexed) {
        args.set(index, JavaString(string));
    }
    return args;
}

void installPython(Activity ctx) {
    value assetManager = ctx.assets;
    value listing = makereader(assetManager.open("listing"));
    value basedir = ctx.filesDir;
    while (exists filename = listing.readLine()) {
        value file = File(basedir, filename.replace("startunderscore_", "_"));
        if (file.\iexists()) {
            Log.d(logtag, "aborting install because ``filename`` already exists");
            return;
        }
        file.parentFile.mkdirs();
        value reader = assetManager.open(filename);
        value writer = FileOutputStream(file);

        Log.d(logtag, "copying ``filename`` to ``file.canonicalPath``");

        copystream(reader, writer);
    }
    Log.d(logtag, "done copying files");
    Log.d(logtag, "making files executable");
    value executables = makereader(assetManager.open("executables"));
    while (exists filename = executables.readLine()) {
        value file = File(basedir, filename);
        Log.d(logtag, "setting permissions on ``filename``");
        value process = Runtime.runtime.exec(toJavaStrings({
            "chmod", "770", file.canonicalPath
        }));
        process.errorStream.close();
        process.inputStream.close();
        process.outputStream.close();
        process.waitFor();
    }
}

Process runPython(Context ctx, String codepath, String* args) {
    // get environment
    value env = HashMap<JavaString,JavaString>(System.getenv());

    // debug prints
    value it = env.entrySet().iterator();
    while (it.hasNext()) {
        Map<JavaString, JavaString>.Entry<JavaString, JavaString> entry = it.next();
        Log.d(logtag, "``entry.key`` -> ``entry.\ivalue``");
    }

    // append python libs dir to LD_LIBRARY_PATH
    JavaString? ldpath = env.get(JavaString("LD_LIBRARY_PATH"));
    value pythonlibs = File(ctx.filesDir, "python-install/lib/");
    String extendedldpath;
    if (exists ldpath) {
        extendedldpath = "``ldpath``:``pythonlibs.canonicalPath``";
    } else {
        extendedldpath = "``pythonlibs.canonicalPath``";
    }
    env.put(JavaString("LD_LIBRARY_PATH"), JavaString(extendedldpath));

    // debug print
    Log.d(logtag, "extendedldpath: ``extendedldpath``");

    // convert map into array of strings of format x=y (see Runtime.exec docs)
    value flattened = ObjectArray<JavaString>(env.size());
    value it2 = env.entrySet().iterator();
    variable value position = 0;
    while (it2.hasNext()) {
        Map<JavaString, JavaString>.Entry<JavaString, JavaString> entry = it2.next();
        flattened.set(position, JavaString("``entry.key``=``entry.\ivalue``"));
        position += 1;
    }

    // debug print
    for (item in flattened.array) {
        Log.d(logtag, "env array item: ``item else "null"``");
    }

    // call runtime.exec
    value pythonbinary = File(ctx.filesDir, "python-install/bin/python");
    value codefile = File(ctx.filesDir, codepath);
    Log.d(logtag, "``pythonbinary`` ``codefile``");
    value process = Runtime.runtime.exec(toJavaStrings({
        pythonbinary.canonicalPath, codefile.canonicalPath,
        *args
    }), flattened);
    return process;
}

shared class MainActivity() extends Activity() {
    variable Process? theprocess = null;
    shared actual void onCreate(Bundle? savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        //testthing();

        //installPython(this);
        //value process = runPython(this, "app/bin/treeoflife-server",
        //        "--android", filesDir.canonicalPath);
        //this.theprocess = process;
        //process.errorStream.close();
        //process.inputStream.close();
        //process.outputStream.close();
    }

    shared void onDerpClick(View view) {
        Log.i(logtag, "Running optimizer test...");
        //Debug.startMethodTracing("optimizer", 1024 * 1024 * 256);
        optimizeRun(void(String msg) => Log.i(logtag, msg), 2);
        //Debug.stopMethodTracing();
        Log.i(logtag, "done running optimizer test");
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




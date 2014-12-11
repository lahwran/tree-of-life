import java.util { JList = List, JArrayList = ArrayList }
import ceylon.interop.java { JavaList, CeylonList }

CeylonList<T> derp<T>(JList<T> x)
        given T satisfies Object {
    return CeylonList<T>(x);
}

shared void run() {
    JList<Integer> x = JArrayList<Integer>();
    x.add(1);
    x.add(null);
    value l = derp<Integer>(x);
    print(l);
}

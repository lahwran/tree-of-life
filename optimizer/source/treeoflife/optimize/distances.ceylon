import ceylon.collection { MapImpl = HashMap, HashSet }

interface DistanceLookup {
    "The list of cities that this object knows about."
    shared formal Genome knownCities;

     "Look up the distance between two cities in km."
    shared formal Integer getDistance(Gene startingCity,
            Gene destinationCity);

    shared default Integer routeLength(Genome candidate) {
        if (!candidate.first exists) {
            return 0;
        }
        assert(exists first = candidate.first);
        value looped = candidate.sequence().withTrailing(first);
        value result = looped.paired.fold(0)
            ((Integer last, [Gene,Gene] pair) =>
                last + getDistance(*pair));
        return result;
    }
}


object europeanDistanceLookup satisfies DistanceLookup {
    value distances = MapImpl<Gene->Gene, Integer>();

    // Distances are in km as the crow flies (from http://www.indo.com/distance/)

    distances.put("Amsterdam"->"Amsterdam", 0);
    distances.put("Amsterdam"->"Athens", 2162);
    distances.put("Amsterdam"->"Berlin", 576);
    distances.put("Amsterdam"->"Brussels", 171);
    distances.put("Amsterdam"->"Copenhagen", 622);
    distances.put("Amsterdam"->"Dublin", 757);
    distances.put("Amsterdam"->"Helsinki", 1506);
    distances.put("Amsterdam"->"Lisbon", 1861);
    distances.put("Amsterdam"->"London", 356);
    distances.put("Amsterdam"->"Luxembourg", 318);
    distances.put("Amsterdam"->"Madrid", 1477);
    distances.put("Amsterdam"->"Paris", 429);
    distances.put("Amsterdam"->"Rome", 1304);
    distances.put("Amsterdam"->"Stockholm", 1132);
    distances.put("Amsterdam"->"Vienna", 938);

    distances.put("Athens"->"Amsterdam", 2162);
    distances.put("Athens"->"Athens", 0);
    distances.put("Athens"->"Berlin", 1801);
    distances.put("Athens"->"Brussels", 2089);
    distances.put("Athens"->"Copenhagen", 2140);
    distances.put("Athens"->"Dublin", 2860);
    distances.put("Athens"->"Helsinki", 2464);
    distances.put("Athens"->"Lisbon", 2854);
    distances.put("Athens"->"London", 2391);
    distances.put("Athens"->"Luxembourg", 1901);
    distances.put("Athens"->"Madrid", 2374);
    distances.put("Athens"->"Paris", 2097);
    distances.put("Athens"->"Rome", 1040);
    distances.put("Athens"->"Stockholm", 2410);
    distances.put("Athens"->"Vienna", 1280);

    distances.put("Berlin"->"Amsterdam", 576);
    distances.put("Berlin"->"Athens", 1801);
    distances.put("Berlin"->"Berlin", 0);
    distances.put("Berlin"->"Brussels", 648);
    distances.put("Berlin"->"Copenhagen", 361);
    distances.put("Berlin"->"Dublin", 1315);
    distances.put("Berlin"->"Helsinki", 1108);
    distances.put("Berlin"->"Lisbon", 2310);
    distances.put("Berlin"->"London", 929);
    distances.put("Berlin"->"Luxembourg", 595);
    distances.put("Berlin"->"Madrid", 1866);
    distances.put("Berlin"->"Paris", 877);
    distances.put("Berlin"->"Rome", 1185);
    distances.put("Berlin"->"Stockholm", 818);
    distances.put("Berlin"->"Vienna", 525);

    distances.put("Brussels"->"Amsterdam", 171);
    distances.put("Brussels"->"Athens", 2089);
    distances.put("Brussels"->"Berlin", 648);
    distances.put("Brussels"->"Brussels", 0);
    distances.put("Brussels"->"Copenhagen", 764);
    distances.put("Brussels"->"Dublin", 780);
    distances.put("Brussels"->"Helsinki", 1649);
    distances.put("Brussels"->"Lisbon", 1713);
    distances.put("Brussels"->"London", 321);
    distances.put("Brussels"->"Luxembourg", 190);
    distances.put("Brussels"->"Madrid", 1315);
    distances.put("Brussels"->"Paris", 266);
    distances.put("Brussels"->"Rome", 1182);
    distances.put("Brussels"->"Stockholm", 1284);
    distances.put("Brussels"->"Vienna", 917);

    distances.put("Copenhagen"->"Amsterdam", 622);
    distances.put("Copenhagen"->"Athens", 2140);
    distances.put("Copenhagen"->"Berlin", 361);
    distances.put("Copenhagen"->"Brussels", 764);
    distances.put("Copenhagen"->"Copenhagen", 0);
    distances.put("Copenhagen"->"Dublin", 1232);
    distances.put("Copenhagen"->"Helsinki", 885);
    distances.put("Copenhagen"->"Lisbon", 2477);
    distances.put("Copenhagen"->"London", 953);
    distances.put("Copenhagen"->"Luxembourg", 799);
    distances.put("Copenhagen"->"Madrid", 2071);
    distances.put("Copenhagen"->"Paris", 1028);
    distances.put("Copenhagen"->"Rome", 1540);
    distances.put("Copenhagen"->"Stockholm", 526);
    distances.put("Copenhagen"->"Vienna", 876);

    distances.put("Dublin"->"Amsterdam", 757);
    distances.put("Dublin"->"Athens", 2860);
    distances.put("Dublin"->"Berlin", 1315);
    distances.put("Dublin"->"Brussels", 780);
    distances.put("Dublin"->"Copenhagen", 1232);
    distances.put("Dublin"->"Dublin", 0);
    distances.put("Dublin"->"Helsinki", 2021);
    distances.put("Dublin"->"Lisbon", 1652);
    distances.put("Dublin"->"London", 469);
    distances.put("Dublin"->"Luxembourg", 961);
    distances.put("Dublin"->"Madrid", 1458);
    distances.put("Dublin"->"Paris", 787);
    distances.put("Dublin"->"Rome", 1903);
    distances.put("Dublin"->"Stockholm", 1625);
    distances.put("Dublin"->"Vienna", 1687);

    distances.put("Helsinki"->"Amsterdam", 1506);
    distances.put("Helsinki"->"Athens", 2464);
    distances.put("Helsinki"->"Berlin", 1108);
    distances.put("Helsinki"->"Brussels", 1649);
    distances.put("Helsinki"->"Copenhagen", 885);
    distances.put("Helsinki"->"Dublin", 2021);
    distances.put("Helsinki"->"Helsinki", 0);
    distances.put("Helsinki"->"Lisbon", 3362);
    distances.put("Helsinki"->"London", 1823);
    distances.put("Helsinki"->"Luxembourg", 1667);
    distances.put("Helsinki"->"Madrid", 2949);
    distances.put("Helsinki"->"Paris", 1912);
    distances.put("Helsinki"->"Rome", 2202);
    distances.put("Helsinki"->"Stockholm", 396);
    distances.put("Helsinki"->"Vienna", 1439);

    distances.put("Lisbon"->"Amsterdam", 1861);
    distances.put("Lisbon"->"Athens", 2854);
    distances.put("Lisbon"->"Berlin", 2310);
    distances.put("Lisbon"->"Brussels", 1713);
    distances.put("Lisbon"->"Copenhagen", 2477);
    distances.put("Lisbon"->"Dublin", 1652);
    distances.put("Lisbon"->"Helsinki", 3362);
    distances.put("Lisbon"->"Lisbon", 0);
    distances.put("Lisbon"->"London", 1585);
    distances.put("Lisbon"->"Luxembourg", 1716);
    distances.put("Lisbon"->"Madrid", 501);
    distances.put("Lisbon"->"Paris", 1452);
    distances.put("Lisbon"->"Rome", 1873);
    distances.put("Lisbon"->"Stockholm", 2993);
    distances.put("Lisbon"->"Vienna", 2300);

    distances.put("London"->"Amsterdam", 356);
    distances.put("London"->"Athens", 2391);
    distances.put("London"->"Berlin", 929);
    distances.put("London"->"Brussels", 321);
    distances.put("London"->"Copenhagen", 953);
    distances.put("London"->"Dublin", 469);
    distances.put("London"->"Helsinki", 1823);
    distances.put("London"->"Lisbon", 1585);
    distances.put("London"->"London", 0);
    distances.put("London"->"Luxembourg", 494);
    distances.put("London"->"Madrid", 1261);
    distances.put("London"->"Paris", 343);
    distances.put("London"->"Rome", 1444);
    distances.put("London"->"Stockholm", 1436);
    distances.put("London"->"Vienna", 1237);

    distances.put("Luxembourg"->"Amsterdam", 318);
    distances.put("Luxembourg"->"Athens", 1901);
    distances.put("Luxembourg"->"Berlin", 595);
    distances.put("Luxembourg"->"Brussels", 190);
    distances.put("Luxembourg"->"Copenhagen", 799);
    distances.put("Luxembourg"->"Dublin", 961);
    distances.put("Luxembourg"->"Helsinki", 1667);
    distances.put("Luxembourg"->"Lisbon", 1716);
    distances.put("Luxembourg"->"London", 494);
    distances.put("Luxembourg"->"Luxembourg", 0);
    distances.put("Luxembourg"->"Madrid", 1282);
    distances.put("Luxembourg"->"Paris", 294);
    distances.put("Luxembourg"->"Rome", 995);
    distances.put("Luxembourg"->"Stockholm", 1325);
    distances.put("Luxembourg"->"Vienna", 761);

    distances.put("Madrid"->"Amsterdam", 1477);
    distances.put("Madrid"->"Athens", 2374);
    distances.put("Madrid"->"Berlin", 1866);
    distances.put("Madrid"->"Brussels", 1315);
    distances.put("Madrid"->"Copenhagen", 2071);
    distances.put("Madrid"->"Dublin", 1458);
    distances.put("Madrid"->"Helsinki", 2949);
    distances.put("Madrid"->"Lisbon", 501);
    distances.put("Madrid"->"London", 1261);
    distances.put("Madrid"->"Luxembourg", 1282);
    distances.put("Madrid"->"Madrid", 0);
    distances.put("Madrid"->"Paris", 1050);
    distances.put("Madrid"->"Rome", 1377);
    distances.put("Madrid"->"Stockholm", 2596);
    distances.put("Madrid"->"Vienna", 1812);

    distances.put("Paris"->"Amsterdam", 429);
    distances.put("Paris"->"Athens", 2097);
    distances.put("Paris"->"Berlin", 877);
    distances.put("Paris"->"Brussels", 266);
    distances.put("Paris"->"Copenhagen", 1028);
    distances.put("Paris"->"Dublin", 787);
    distances.put("Paris"->"Helsinki", 1912);
    distances.put("Paris"->"Lisbon", 1452);
    distances.put("Paris"->"London", 343);
    distances.put("Paris"->"Luxembourg", 294);
    distances.put("Paris"->"Madrid", 1050);
    distances.put("Paris"->"Paris", 0);
    distances.put("Paris"->"Rome", 1117);
    distances.put("Paris"->"Stockholm", 1549);
    distances.put("Paris"->"Vienna", 1037);

    distances.put("Rome"->"Amsterdam", 1304);
    distances.put("Rome"->"Athens", 1040);
    distances.put("Rome"->"Berlin", 1185);
    distances.put("Rome"->"Brussels", 1182);
    distances.put("Rome"->"Copenhagen", 1540);
    distances.put("Rome"->"Dublin", 1903);
    distances.put("Rome"->"Helsinki", 2202);
    distances.put("Rome"->"Lisbon", 1873);
    distances.put("Rome"->"London", 1444);
    distances.put("Rome"->"Luxembourg", 995);
    distances.put("Rome"->"Madrid", 1377);
    distances.put("Rome"->"Paris", 1117);
    distances.put("Rome"->"Rome", 0);
    distances.put("Rome"->"Stockholm", 1984);
    distances.put("Rome"->"Vienna", 765);

    distances.put("Stockholm"->"Amsterdam", 1132);
    distances.put("Stockholm"->"Athens", 2410);
    distances.put("Stockholm"->"Berlin", 818);
    distances.put("Stockholm"->"Brussels", 1284);
    distances.put("Stockholm"->"Copenhagen", 526);
    distances.put("Stockholm"->"Dublin", 1625);
    distances.put("Stockholm"->"Helsinki", 396);
    distances.put("Stockholm"->"Lisbon", 2993);
    distances.put("Stockholm"->"London", 1436);
    distances.put("Stockholm"->"Luxembourg", 1325);
    distances.put("Stockholm"->"Madrid", 2596);
    distances.put("Stockholm"->"Paris", 1549);
    distances.put("Stockholm"->"Rome", 1984);
    distances.put("Stockholm"->"Stockholm", 0);
    distances.put("Stockholm"->"Vienna", 1247);

    distances.put("Vienna"->"Amsterdam", 938);
    distances.put("Vienna"->"Athens", 1280);
    distances.put("Vienna"->"Berlin", 525);
    distances.put("Vienna"->"Brussels", 917);
    distances.put("Vienna"->"Copenhagen", 876);
    distances.put("Vienna"->"Dublin", 1687);
    distances.put("Vienna"->"Helsinki", 1439);
    distances.put("Vienna"->"Lisbon", 2300);
    distances.put("Vienna"->"London", 1237);
    distances.put("Vienna"->"Luxembourg", 761);
    distances.put("Vienna"->"Madrid", 1812);
    distances.put("Vienna"->"Paris", 1037);
    distances.put("Vienna"->"Rome", 765);
    distances.put("Vienna"->"Stockholm", 1247);
    distances.put("Vienna"->"Vienna", 0);

    value keyKeys = distances.keys*.key;
    shared actual Genome knownCities = HashSet{ *keyKeys }.sequence();

    shared actual Integer getDistance(Gene startingCity,
            Gene destinationCity) {
        assert(exists distance = distances.get(startingCity->destinationCity));
        return distance;
    }
}

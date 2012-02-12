const Cc = Components.classes;
const Ci = Components.interfaces;
const Cr = Components.results;

function run_test()
{
    var s = Cc["@mozilla.org/io/string-input-stream;1"]
              .createInstance(Ci.nsIStringInputStream);
    var body =
"foo:bar\\u0020\\u61\\u\n\
# this is a comment\n\
9=this is the first part of a continued line \\\n\
 and here is the 2nd part\n\
mark=this is a string \\\n\
# possibly a comment \\\n\
and trail\n\
foz=baz\n";
    s.setData(body, body.length);
    var props = Cc["@mozilla.org/persistent-properties;1"]
                  .createInstance(Ci.nsIPersistentProperties);
    props.load(s);
    var p_enum = props.enumerate();
    while (p_enum.hasMoreElements()) {
      var p = p_enum.getNext().QueryInterface(Ci.nsIPropertyElement);
      print("key: " + p.key);
      print(p.value);
    }
}
run_test()
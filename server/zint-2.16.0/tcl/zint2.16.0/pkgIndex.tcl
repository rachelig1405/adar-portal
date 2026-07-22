if {[package vsatisfies [package provide Tcl] 9.0-]} { 
package ifneeded zint 2.16.0 [list load [file join $dir tcl9zint2160.dll]] 
} else { 
package ifneeded zint 2.16.0 [list load [file join $dir zint2160t.dll]] 
} 

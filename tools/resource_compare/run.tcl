set script_path [file normalize [info script]]
set script_dir [file dirname $script_path]
set root [file normalize [file join $script_dir ".." ".."]]
set variant $env(DSM_RESOURCE_VARIANT)
set build_root [file normalize $env(DSM_RESOURCE_BUILD)]
set project_dir [file join $build_root $variant]
set filelist [file join $build_root "${variant}.f"]
file mkdir $build_root
set f [open $filelist w]
set rtl_filelist [file join $root "gndless_delta_sigma.f"]
set input [open $rtl_filelist r]
puts $f [read $input]
close $input
puts $f [file join $script_dir "top.sv"]
puts $f [file join $script_dir "top.sdc"]
close $f
# 比較用projectのPnR設定が残らないよう、生成物だけを破棄する。
file delete -force [file join $project_dir "resource_${variant}" "impl"]
create_project -name "resource_${variant}" -dir $project_dir -pn "GW5A-LV25MG121NC1/I0" -device_version "A" -force
set_option -verilog_std sysv2017
set top_module "second_${variant}_top"
set_option -top_module $top_module
set_option -timing_driven 1
set_option -correct_hold_violation 1
set_option -route_maxfan 50
set_option -ireg_in_iob 0
set_option -oreg_in_iob 0
set_option -ioreg_in_iob 0
set_option -use_cpu_as_gpio 1
set_option -use_ready_as_gpio 1
set_option -use_jtag_as_gpio 0
set_option -use_sspi_as_gpio 1
set_option -use_mspi_as_gpio 0
set_option -use_done_as_gpio 0
set_option -use_mode_as_gpio 0
set_option -use_i2c_as_gpio 0
set_option -cst_warn_to_error 0
set_option -place_option 1
set_option -route_option 2
import_files -fileList $filelist -force
run all
run close
exit

create_clock -name waveform_clk -period 20.000 [get_ports {clk}]
set_false_path -from [get_ports {rst}]

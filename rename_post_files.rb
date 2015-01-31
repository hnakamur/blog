#!/usr/bin/env ruby
require 'fileutils'

Dir.glob("content/post/*.markdown") do |f|
  dir = File.dirname(f)
  base = File.basename(f)
  m = /\A(\d+)-(\d+)-(\d+)-(.*)\z/.match base
  to_dir = File.join(dir, m[1], m[2], m[3])
  FileUtils.makedirs to_dir
  FileUtils.mv f, File.join(to_dir, m[4])
end

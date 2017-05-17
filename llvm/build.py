#!/usr/bin/python


import sys, os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".."))
import build_support as bs

opts = [
    '-DCMAKE_BUILD_TYPE=Release',
    '-DLLVM_ENABLE_ASSERTIONS:BOOL=ON',
    '-DLLVM_TARGETS_TO_BUILD:STRING=AMDGPU;X86',
    '-DLLVM_BUILD_LLVM_DYLIB:BOOL=ON',
    '-DLLVM_LINK_LLVM_DYLIB:BOOL=ON',
]

builder = bs.CMakeBuilder(extra_definitions=opts)

bs.build(builder)

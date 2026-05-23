#!/usr/bin/env sh
path="$CHEF_HOME/installed/$PACKAGE_NAME"
nproc=

if [ "$OS" = "LINUX" ]; then
    nproc=$(nproc)
else
    nproc=$(sysctl -n hw.logicalcpu)
fi

if [ -d "$path" ]; then
    rm -rf "$path"
else
    mkdir "$path"
fi

./configure \
    --enable-optimizations \
    --prefix="$path"

make -j$nproc
make install

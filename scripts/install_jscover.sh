#!/usr/bin/env bash

# Install dependencies for acceptance tests
# Run from the repo root

LETTUCE_FIXTURES_DIR=js_test_tool/features/fixtures
JS_LIB_DIR=$LETTUCE_FIXTURES_DIR/jasmine/lib
JSCOVER_DIR=$LETTUCE_FIXTURES_DIR/jscover

JSCOVER_URL=http://iweb.dl.sourceforge.net/project/jscover/JSCover-0.3.0.zip
JQUERY_URL=http://code.jquery.com/jquery-1.10.1.min.js
JASMINE_JQUERY_URL=https://raw.github.com/velesin/jasmine-jquery/master/lib/jasmine-jquery.js 

mkdir -p $JSCOVER_DIR

if [ ! -f $JSCOVER_DIR/target/dist/JSCover-all.jar ];
then
    curl $JSCOVER_URL > $JSCOVER_DIR/jscover.zip
    unzip $JSCOVER_DIR/jscover.zip target/dist/JSCover-all.jar -d $JSCOVER_DIR
fi

mkdir -p $JS_LIB_DIR
if [ ! -f $JS_LIB_DIR/jquery.js ];
then
    curl $JQUERY_URL > $JS_LIB_DIR/jquery.js
fi
#
if [ ! -f $JS_LIB_DIR/jasmine-jquery.js ];
then
    curl $JASMINE_JQUERY_URL > $JS_LIB_DIR/jasmine-jquery.js
fi

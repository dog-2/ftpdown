#!/usr/bin/env python
# encoding: utf-8

import os
import sys
import ftplib
import traceback


class FtpDownloader(object):
    PATH_TYPE_UNKNOWN = -1
    PATH_TYPE_FILE = 0
    PATH_TYPE_DIR = 1

    def __init__(self, host, user=None, passwd=None, port=21, timeout=10):
        self.conn = ftplib.FTP(
            host=host,
            user=user,
            passwd=passwd,
            timeout=timeout
        )

    def dir(self, *args):
        '''
        by defualt, ftplib.FTP.dir() does not return any value.
        Instead, it prints the dir info to the stdout.
        So we re-implement it in FtpDownloader, which is able to return the dir info.
        '''
        info = []
        cmd = 'LIST'
        for arg in args:
            if arg:
                cmd = cmd + (' ' + arg)
        self.conn.retrlines(cmd, lambda x: info.append(x.strip().split()))
        return info

    def tree(self, rdir=None, init=True):
        '''
        recursively get the tree structure of a directory on FTP Server.
        args:
            rdir - remote direcotry path of the FTP Server.
            init - flag showing whether in a recursion.
        '''
        if init and rdir in ('.', None):
            rdir = self.conn.pwd()
        tree = []
        tree.append((rdir, self.PATH_TYPE_DIR))

        dir_info = self.dir(rdir)
        for info in dir_info:
            attr = info[0]  # attribute
            name = info[-1]
            path = os.path.join(rdir, name)
            if attr.startswith('-'):
                tree.append((path, self.PATH_TYPE_FILE))
            elif attr.startswith('d'):
                if (name == '.' or name == '..'):  # skip . and ..
                    continue
                tree.extend(self.tree(rdir=path,init=False))  # recurse
            else:
                tree.append(path, self.PATH_TYPE_UNKNOWN)

        return tree

    def downloadFile(self, rfile, lfile):
        '''
        download a file with path %rfile on a FTP Server and save it to locate
        path %lfile.
        '''
        ldir = os.path.dirname(lfile)
        if not os.path.exists(ldir):
            os.makedirs(ldir)
        f = open(lfile, 'wb')
        self.conn.retrbinary('RETR %s' % rfile, f.write)
        f.close()
        return True

    def treeStat(self, tree):
        numDir = 0
        numFile = 0
        numUnknown = 0
        for path, pathType in tree:
            if pathType == self.PATH_TYPE_DIR:
                numDir += 1
            elif pathType == self.PATH_TYPE_FILE:
                numFile += 1
            elif pathType == self.PATH_TYPE_UNKNOWN:
                numUnknown += 1
        return numDir, numFile, numUnknown


    def downloadDir(self, rdir='.', ldir='.', tree=None,
                    errHandleFunc=None, verbose=True):
        '''
        download a direcotry with path %rdir on a FTP Server and save it to
        locate path %ldir.
        args:
            tree - the tree structure return by function FtpDownloader.tree()
            errHandleFunc - error handling function when error happens in
                downloading one file, such as a function that writes a log.
                By default, the error is print to the stdout.
        '''
        if not tree:
            tree = self.tree(rdir=rdir, init=True)
        numDir, numFile, numUnknown = self.treeStat(tree)
        if verbose:
            print 'Host %s tree statistic:' % self.conn.host
            print '%d directories, %d files, %d unknown type' % (
                numDir,
                numFile,
                numUnknown
            )

        if not os.path.exists(ldir):
            os.makedirs(ldir)
        ldir = os.path.abspath(ldir)

        numDownOk = 0
        numDownErr = 0
        for rpath, pathType in tree:
            lpath = os.path.join(ldir, rpath.strip('/').strip('\\'))
            if pathType == self.PATH_TYPE_DIR:
                if not os.path.exists(lpath):
                    os.makedirs(lpath)
            elif pathType == self.PATH_TYPE_FILE:
                try:
                    self.downloadFile(rpath, lpath)
                    numDownOk += 1
                except Exception as err:
                    numDownErr += 1
                    if errHandleFunc:
                        errHandleFunc(err, rpath, lpath)
                    elif verbose:
                        print 'An Error occurred when downloading '\
                              'remote file %s' % rpath
                        traceback.print_exc()
                        print
                if verbose:
                    print 'Host %s: %d/%d/%d(ok/err/total) files downloaded' % (
                        self.conn.host,
                        numDownOk,
                        numDownErr,
                        numFile
                    )
            elif pathType == self.PATH_TYPE_UNKNOWN:
                if verbose:
                    print 'Unknown type romote path got: %s' % rpath

        if verbose:
            print 'Host %s directory %s download finished:' % (
                self.conn.host, rdir
            )
            print '%d directories, %d(%d failed) files, %d unknown type.' % (
                numDir,
                numFile,
                numDownErr,
                numUnknown
            )
        return numDir, numFile, numUnknown, numDownErr


if __name__ == '__main__':
    import sys
    import traceback
    from pprint import pprint as pr

    flog = open('err.log', 'wb')

    def run(host):
        try:
            fd = FtpDownloader(
                host=host,
                user='test',
                passwd='test',
                port=21,
                timeout=10
            )
            numDir, numFile, numUnknown, numDownErr = fd.downloadDir(
                rdir='.',
                ldir='download',
                tree=None,
                errHandleFunc=None,
                verbose=True
            )
            flog.write(
                '%s\nok\n'
                '%d directories, %d(%d failed) files, %d unknown type\n\n\n' % (
                    host,
                    numDir,
                    numFile,
                    numDownErr,
                    numUnknown
                )
            )
        except Exception as err:
            traceback.print_exc()
            flog.write(
                '%s\nerror\n%s\n\n\n' % (
                    host,
                    traceback.format_exc()
                )
            )

    pr(run(sys.argv[1]))
    flog.close()
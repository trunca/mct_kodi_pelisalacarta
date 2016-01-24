# -*- coding: utf-8 -*-
#------------------------------------------------------------
# pelisalacarta - XBMC Plugin
# MCT - Mini Cliente Torrent para pelisalacarta
# http://blog.tvalacarta.info/plugin-xbmc/pelisalacarta/
#------------------------------------------------------------
import urlparse,urllib2,urllib,re
import os
import sys

import shutil, tempfile

import libtorrent as lt

import xbmc
import xbmcgui

from platformcode import library

from core import scrapertools
from core import config

import time
time_sleep = 2

__pieces__ = 5

def play(url, is_view=None):

    # -- Necesario para algunas webs -------------------------- -
    if not url.endswith(".torrent") and not url.startswith("magnet"):
        t_file = scrapertools.get_header_from_response(url,header_to_get="location")
        if len(t_file) > 0:
            url = t_file
            t_file = scrapertools.get_header_from_response(url,header_to_get="location")
        if len(t_file) > 0:
            url = t_file

    # -- Crear dos carpetas en descargas para los archivos ------
    save_path_videos = os.path.join( config.get_setting("downloadpath") , "torrent-videos" )
    save_path_torrents = os.path.join( config.get_setting("downloadpath") , "torrent-torrents" )
    if not os.path.exists( save_path_torrents ): os.mkdir(save_path_torrents)

    # -- Usar - archivo torrent desde web, meagnet o HD ---------
    if not os.path.isfile(url) and not url.startswith("magnet"):
        # -- http - crear archivo torrent -----------------------
        data = url_get(url)
        # -- El nombre del torrent será el que contiene en los --
        # -- datos.                                             -
        #re_name_len = int( scrapertools.get_match(data,':name(\d+):') )
        re_name = library.title_to_folder_name( urllib.unquote( scrapertools.get_match(data,':name\d+:(.*?)\d+:') ) )
        torrent_file = os.path.join(save_path_torrents, re_name+'.torrent')

        f = open(torrent_file,'wb')
        f.write(data)
        f.close()
    elif os.path.isfile(url):
        # -- file - para usar torrens desde el HD ---------------
        torrent_file = url
    else:
        # -- magnet ---------------------------------------------
        torrent_file = url
    # -----------------------------------------------------------

    # -- MCT - MiniClienteTorrent -------------------------------
    ses = lt.session()

    print "#########################"
    print lt.version
    print "#########################"

    ses.add_dht_router("router.bittorrent.com",6881)
    ses.add_dht_router("router.utorrent.com",6881)
    ses.add_dht_router("router.bitcomet.com",554)
    ses.add_dht_router("dht.transmissionbt.com",6881)

    trackers = [
        "http://exodus.desync.com:6969/announce",
        "udp://tracker.publicbt.com:80/announce",
        "udp://tracker.openbittorrent.com:80/announce",
        "http://tracker.torrentbay.to:6969/announce",
        "http://fr33dom.h33t.com:3310/announce",
        "http://tracker.pow7.com/announce",
        "udp://tracker.ccc.de:80/announce",
        "http://tracker.bittorrent.am:80/announce",
        "http://denis.stalker.h3q.com:6969/announce",
        "udp://tracker.prq.to:80/announce",
        "udp://tracker.istole.it:80/announce",
        "udp://open.demonii.com:1337",

        "http://9.rarbg.com:2710/announce",
        "http://announce.torrentsmd.com:6969/announce",
        "http://bt.careland.com.cn:6969/announce",
        "http://explodie.org:6969/announce",
        "http://mgtracker.org:2710/announce",
        "http://tracker.best-torrents.net:6969/announce",
        "http://tracker.tfile.me/announce",
        "http://tracker.torrenty.org:6969/announce",
        "http://tracker1.wasabii.com.tw:6969/announce",
        "udp://9.rarbg.com:2710/announce",
        "udp://9.rarbg.me:2710/announce",
        "udp://coppersurfer.tk:6969/announce",
        "udp://tracker.btzoo.eu:80/announce",

        "http://www.spanishtracker.com:2710/announce",
        "http://www.todotorrents.com:2710/announce",
    ]

    video_file = ""
    ## -- magnet2torrent ----------------------------------------
    if torrent_file.startswith("magnet"):
        tempdir = tempfile.mkdtemp()
        params = {
            'save_path': tempdir,
            'trackers':trackers,
            'storage_mode': lt.storage_mode_t.storage_mode_allocate,
            'paused': False,
            'auto_managed': True,
            'duplicate_is_error': True
        }
        h = lt.add_magnet_uri(ses, torrent_file, params)
        dp = xbmcgui.DialogProgress()
        dp.create('pelisalacarta-MCT')
        while not h.has_metadata():
            message, porcent, msg_file, s, download = getProgress(h, "Creando torrent desde magnet")
            dp.update(porcent, message, msg_file)
        dp.close()
        info = h.get_torrent_info()
        data = lt.bencode( lt.create_torrent(info).generate() )
        torrent_file = os.path.join(save_path_torrents, info.name() + ".torrent")
        f = open(torrent_file,'wb')
        f.write(data)
        f.close()
        ses.remove_torrent(h)
        shutil.rmtree(tempdir)
    # -----------------------------------------------------------

    # -- Archivos torrent ---------------------------------------
    e = lt.bdecode(open(torrent_file, 'rb').read())
    info = lt.torrent_info(e)

    # -- El más gordo o uno de los más gordo se entiende que es -
    # -- el vídeo o es el vídeo que se usará como referencia    -
    # -- para el tipo de archivo                                -
    _index_file, _video_file, _size_file = get_video_file(info)

    if not _video_file.endswith('.avi'):
        print "##### storage_mode_t.storage_mode_sparse (no avi) #####"
        h = ses.add_torrent( { 'ti':info, 'save_path': save_path_videos, 'trackers':trackers, 'storage_mode':lt.storage_mode_t.storage_mode_sparse } )
    else:
        print "##### storage_mode_t.storage_mode_allocate (avi) #####"
        h = ses.add_torrent( { 'ti':info, 'save_path': save_path_videos, 'trackers':trackers, 'storage_mode':lt.storage_mode_t.storage_mode_allocate } )
    ## ----------------------------------------------------------

    # -- Prioritarizar ------------------------------------------
    _index, video_file, video_size = get_video_files_sizes( info )
    if _index == -1:
        _index = _index_file
        video_file = _video_file
        video_size = _size_file

    piece_set = set_priority_pieces(h, _index, video_file, video_size, _log=True)

    # -- Descarga secuencial - trozo 1, trozo 2, ... ------------
    #h.set_sequential_download(True)

    h.force_reannounce()
    h.force_dht_announce()

    # -- Crear diálogo de progreso para el primer bucle ---------
    dp = xbmcgui.DialogProgress()
    dp.create('pelisalacarta-MCT')

    # -- Para log -----------------------------------------------
    timer = time.time()

    # -- Local con el número de piezas por cluster global -------
    _cluster_pieces = __pieces__

    '''
    # -- Estimar cuando se comenzará el visionado ---------------
    # -- Pruebas: Porcentaje fijo                               -
    porcentage_to_play = 1.50
    '''

    # -- Estimar cuando se comenzará el visionado ---------------
    # -- Pruebas: Porcentaje segun tamaño cuando sólo hay un    -
    # -- vídeo en torrent                                       -
    porcentage_to_play = set_porcentage_to_play(video_size)

    # -- Doble bucle anidado ------------------------------------
    # -- Descarga - Primer bucle                                -
    while not h.is_seed():
        s = h.status()

        xbmc.sleep(100)

        # -- Recuperar los datos del progreso -------------------
        message, porcent, msg_file, s, download = getProgress(h, video_file)

        # -- Si hace 'checking' existe descarga -----------------
        # -- 'download' Se usará para saber si hay datos        -
        # -- descargados para el diálogo de 'remove_files'      -
        if s.state == 1: download = 1

        # -- Añadido: Log para las pruebas ----------------------
        # -- Print log have_piece. Procedimiento al final del   -
        # -- archivo                                            -
        timer2 = time.time() - timer
        if timer2 > time_sleep:
            print_have_piece_set(h, piece_set)
            timer = time.time()

            # -- Print log y procedimiento incrementar cluster --
            # -- Parte 1                                        -
            _cluster = False
            if _cluster_pieces < len(piece_set):
                _cluster = \
                    cluster_stat(
                        h,
                        piece_set[_cluster_pieces - __pieces__],
                        piece_set[_cluster_pieces],
                        _log=True
                    )
            else: _cluster_pieces = len(piece_set) -1
            # -- Parte 2                                        -
            if _cluster:
                _cluster_pieces+= __pieces__
                cluster_set(h, _cluster_pieces, piece_set, 7, _log=True)

                _cluster_pieces2 = _cluster_pieces + __pieces__
                cluster_set(h, _cluster_pieces2, piece_set, 6, _log=True)

                _cluster_pieces3 = _cluster_pieces2 + __pieces__
                cluster_set(h, _cluster_pieces3, piece_set, 5, _log=True)

        # -- Player - play --------------------------------------
        option_view = ( (s.progress * 100) >= porcentage_to_play )

        # -- Modificado: Se tendrá en cuenta el primer cluster --
        # -- completado para el inicio de la reproducción       -
        first_cluster = True
        _p = "##### first_cluster: "
        for i in range( piece_set[0], piece_set[__pieces__] ):
            _p+= "[%s:%s]" % ( i, h.have_piece(i) )
            first_cluster&= h.have_piece(i)
        print _p

        if (option_view and is_view != "Ok" and s.state == 3 and first_cluster ):
            print "##### porcentage_to_play ## %s ##" % porcentage_to_play

            is_view = "Ok"
            dp.close()

            # -- Player - Ver el vídeo --------------------------
            player = play_video()
            player.play( os.path.join( save_path_videos, video_file ) )

            # -- Segundo bucle - Player - Control de eventos ----
            while player.isPlaying():
                xbmc.sleep(100)

                # -- Añadido: Log para las pruebas --------------
                # -- Print log have_piece. Procedimiento al     -
                # -- final del archivo                          -
                timer2 = time.time() - timer
                if timer2 > time_sleep:
                    print_have_piece_set(h, piece_set)
                    timer = time.time()

                    # -- Print log y procedimiento incrementar --
                    # -- cluster                                -
                    # -- Parte 1                                -
                    _cluster = False
                    if _cluster_pieces < len(piece_set):
                        _cluster = \
                            cluster_stat(
                                h,
                                piece_set[_cluster_pieces - __pieces__],
                                piece_set[_cluster_pieces],
                                _log=True
                            )
                    else: _cluster_pieces = len(piece_set) -1
                    # -- Parte 2                                -
                    if _cluster:
                        _cluster_pieces+= __pieces__
                        cluster_set(h, _cluster_pieces, piece_set, 7, _log=True)

                        _cluster_pieces2 = _cluster_pieces + __pieces__
                        cluster_set(h, _cluster_pieces2, piece_set, 6, _log=True)

                        _cluster_pieces3 = _cluster_pieces2 + __pieces__
                        cluster_set(h, _cluster_pieces3, piece_set, 5, _log=True)

                # -- Cerrar el diálogo de progreso --------------
                if player.resumed:
                    dp.close()

                # -- Mostrar el diálogo de progreso -------------
                if player.paused:
                    # -- Crear diálogo si no existe -------------
                    if not player.statusDialogoProgress:
                        dp = xbmcgui.DialogProgress()
                        dp.create('pelisalacarta-MCT')
                        player.setDialogoProgress()

                    # -- Diálogos de estado en el visionado -----
                    if not h.is_seed():
                        # -- Recuperar los datos del progreso ---
                        message, porcent, msg_file, s, download = getProgress(h, video_file)
                        dp.update(porcent, message, msg_file)
                    else:
                        dp.update(100, "Descarga completa: " + video_file)

                    # -- Se canceló el progreso en el visionado -
                    # -- Continuar                              -
                    if dp.iscanceled():
                        dp.close()
                        player.pause()

                    # -- El usuario cancelo el visionado --------
                    # -- Terminar                               -
                    if player.ended:
                        _index, video_file, video_size = get_video_files_sizes( info )
                        if _index == -1:
                            # -- Diálogo eliminar archivos ----------
                            remove_files( download, torrent_file, video_file, ses, h )
                            return
                        else:
                            set_porcentage_to_play(video_size)
                            piece_set = set_priority_pieces(h, _index, video_file, video_size, _log=True)

        # -- Kodi - Se cerró el visionado -----------------------
        # -- Continuar | Terminar                               -
        if is_view == "Ok" and not xbmc.Player().isPlaying():

            # -- Diálogo continuar o terminar -------------------
            d = xbmcgui.Dialog()
            ok = d.yesno('pelisalacarta-MCT', 'XBMC-Kodi Cerró el vídeo.', '¿Continuar con la sesión?')

            # -- SI -------------------------------------------------
            if ok:
                # -- Continuar --------------------------------------
                is_view=None
            else:
                # -- Terminar ---------------------------------------
                _index, video_file, video_size = get_video_files_sizes( info )
                if _index == -1:
                    # -- Diálogo eliminar archivos                      -
                    remove_files( download, torrent_file, video_file, ses, h )
                    return
                else:
                    set_porcentage_to_play(video_size)
                    piece_set = set_priority_pieces(h, _index, video_file, video_size, _log=True)
                    is_view=None
                    dp = xbmcgui.DialogProgress()
                    dp.create('pelisalacarta-MCT')

        # -- Mostar progeso antes del visionado -----------------
        if is_view != "Ok" :
            dp.update(porcent, message, msg_file)

        # -- Se canceló el progreso antes del visionado ---------
        # -- Terminar                                           -
        if dp.iscanceled():
            dp.close()
            _index, video_file, video_size = get_video_files_sizes( info )
            if _index == -1:
                # -- Diálogo eliminar archivos ----------------------
                remove_files( download, torrent_file, video_file, ses, h )
                return
            else:
                set_porcentage_to_play(video_size)
                piece_set = set_priority_pieces(h, _index, video_file, video_size, _log=True)
                is_view=None
                dp = xbmcgui.DialogProgress()
                dp.create('pelisalacarta-MCT')

    # -- Kodi - Error? - No debería llegar aquí -----------------
    if is_view == "Ok" and not xbmc.Player().isPlaying():
        dp.close()
        # -- Diálogo eliminar archivos --------------------------
        remove_files( download, torrent_file, video_file, ses, h )

    return

# -- Progreso de la descarga ------------------------------------
def getProgress(h, video_file):

    s = h.status()

    state_str = ['queued', 'checking', 'downloading metadata', \
        'downloading', 'finished', 'seeding', 'allocating', 'checking fastresume']

    message = '%.2f%% d:%.1f kb/s u:%.1f kb/s p:%d s:%d %s' % \
        (s.progress * 100, s.download_rate / 1000, s.upload_rate / 1000, \
        s.num_peers, s.num_seeds, state_str[s.state])
    porcent = int( s.progress * 100 )

    download = ( s.progress * 100 )

    if "/" in video_file: video_file = video_file.split("/")[1]
    msg_file = "..../"+video_file + " (%.2f)" % (s.total_wanted/1048576.0)

    return (message, porcent, msg_file, s, download)

# -- Clase play_video - Controlar eventos -----------------------
class play_video(xbmc.Player):

    def __init__( self, *args, **kwargs ):
        self.paused = False
        self.resumed = True
        self.statusDialogoProgress = False
        self.ended = False

    def onPlayBackPaused(self):
        self.paused = True
        self.resumed = False

    def onPlayBackResumed(self):
        self.paused = False
        self.resumed = True
        self.statusDialogoProgress = False

    def is_paused(self):
        return self.paused

    def setDialogoProgress(self):
        self.statusDialogoProgress = True

    def is_started(self):
        self.ended = False

    def is_ended(self):
        self.ended = True

# -- Conseguir el nombre un alchivo de vídeo del metadata -------
# -- El más gordo o uno de los más gordo se entiende que es el  -
# -- vídeo o es vídeo que se usará como referencia para el tipo -
# -- de archivo                                                 -
def get_video_file( info ):
    size_file = 0
    for i, f in enumerate(info.files()):
        if f.size > size_file:
            video_file = f.path.replace("\\","/")
            size_file = f.size
            index_file = i
    return index_file, video_file, size_file

# -- Listado de selección del vídeo a prioritarizar -------------
def get_video_files_sizes( info ):

    opciones = []
    vfile_name = {}
    vfile_size = {}

    for i, f in enumerate( info.files() ):
        _index = int(i)
        _title = f.path.replace("\\","/").decode('utf-8')
        _size = f.size
        _offset = f.offset

        _file_name = os.path.splitext( _title )[0]
        if "/" in _file_name: _file_name = _file_name.split('/')[1]

        _file_ext = os.path.splitext( _title )[1]

        _caption = str(i) + \
            " - " + \
            _file_name + \
            "[" + \
            _file_ext + \
            ":" + \
            str(_size) + \
            "]"

        vfile_name[i] = _title
        vfile_size[i] = _size

        opciones.append(_caption)

    if len(opciones) > 1:
        d = xbmcgui.Dialog()
        seleccion = d.select("pelisalacarta-MCT: Lista de vídeos", opciones)
    else: seleccion = 0

    if seleccion == -1:
        vfile_name[seleccion] = ""
        vfile_size[seleccion] = 0

    return seleccion, vfile_name[seleccion], vfile_size[seleccion]

# -- Preguntar si se desea borrar lo descargado -----------------
def remove_files( download, torrent_file, video_file, ses, h ):

    dialog_view = False
    torrent = False

    if os.path.isfile( torrent_file ):
        dialog_view = True
        torrent = True

    if download > 0:
        dialog_view = True

    if "/" in video_file: video_file = video_file.split("/")[0]

    if dialog_view:
        d = xbmcgui.Dialog()
        ok = d.yesno('pelisalacarta-MCT', 'Borrar las descargas del video', video_file)

        # -- SI -------------------------------------------------
        if ok:
            # -- Borrar archivo - torrent -----------------------
            if torrent:
                os.remove( torrent_file )
            # -- Borrar carpeta/archivos y sesión - vídeo -------
            ses.remove_torrent( h, 1 )
        else:
            # -- Borrar sesión ----------------------------------
            ses.remove_torrent( h )
    else:
        # -- Borrar sesión ----------------------------------
        ses.remove_torrent( h )

    return

# -- Descargar de la web los datos para crear el torrent --------
# -- Si queremos aligerar el script mct.py se puede importar la -
# -- función del conentor torrent.py                            -
def url_get(url, params={}, headers={}):
    from contextlib import closing

    USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:20.0) Gecko/20100101 Firefox/20.0"

    if params:
        import urllib
        url = "%s?%s" % (url, urllib.urlencode(params))

    req = urllib2.Request(url)
    req.add_header("User-Agent", USER_AGENT)

    for k, v in headers.items():
        req.add_header(k, v)

    try:
        with closing(urllib2.urlopen(req)) as response:
            data = response.read()
            if response.headers.get("Content-Encoding", "") == "gzip":
                import zlib
                return zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(data)
            return data
    except urllib2.HTTPError:
        return None

# -- Procedimiento para log de have_piece en las -----------
# -- pruebas                                               -
def print_have_piece_set(h, piece_set):
    c = 0
    _print = "##### %s piezas descargadas de %s\n" % ( h.status().num_pieces, len(piece_set) )
    for i, _set in enumerate(piece_set):
        if h.have_piece(_set):
            _print+= "[%s]" % str(_set).zfill(5)
        else: _print+= "[XXXXX]"
        c+= 1
        if c == 20:
            c = 0
            _print+= "\n"
    print _print

def cluster_stat(h, _start, _end, _log=False):
    _cluster = True
    if _log: _print = "##### range( %s, %s )\n##### " % ( _start, _end )
    for i in range( _start, _end ):
        if _log: _print+= "[%s:%s]" % ( i, h.have_piece(i) )
        _cluster&= h.have_piece(i)
    return _cluster

def cluster_set(h, _cluster_pieces, piece_set, _set, _log=False):
    if _log: _print = "##########################################################################################\n"
    if _log: _print+= "_cluster_pieces: %s\n" % _cluster_pieces
    if _log: _print+= "------------------------------------------------------------------------------------------\n"
    if _cluster_pieces > len(piece_set) - 1:
        _cluster_pieces = len(piece_set) - 1
    if _log: _print+= "cluster[%s:%s]\n" % ( str(piece_set[_cluster_pieces - __pieces__]).zfill(5), str(piece_set[_cluster_pieces] - 1).zfill(5) )
    for i in range( _cluster_pieces - __pieces__, _cluster_pieces ):
        if _log: _print+= "h.piece_priority( piece_set[%s], %s )\n" % ( i, _set )
        h.piece_priority( piece_set[i], _set )
        #if _log: _print+= "[%s]" % h.piece_priority(piece_set[i])
    if _log: print _print
    if _log: _print+= "\n##########################################################################################"

def set_porcentage_to_play(video_size):
    default_porcent_to_play = 0.50
    if video_size >  1000000000: default_porcent_to_play = 0.50
    if video_size >  1500000000: default_porcent_to_play = 0.60
    if video_size >  2500000000: default_porcent_to_play = 0.70
    if video_size >  5000000000: default_porcent_to_play = 0.75
    if video_size > 10000000000: default_porcent_to_play = 0.20
    if video_size > 15000000000: default_porcent_to_play = 0.175
    if video_size > 20000000000: default_porcent_to_play = 0.125
    return (video_size/(video_size * 0.4)) * default_porcent_to_play

def set_priority_pieces(h, _index, video_file, video_size, _log=False):
    if _log:
        print "#### h.file_priorities() ## %s ##" % h.file_priorities()
        print "#### h.piece_priorities() ## %s ##" % h.piece_priorities()
        print "#### _index ## %s ##" % _index
        print "#### video_file ## %s ##" % video_file
        print "#### video_size ## %s ##" % video_size

    for i, _set in enumerate(h.file_priorities()):
        if i != _index:
            h.file_priority(i,0)
        else:
            h.file_priority(i,1)

    piece_set = []
    for i, _set in enumerate(h.piece_priorities()):
        if _set == 1:
            piece_set.append(i)

    #-- Prioritarizar los tres primeros clusters ----------------
    for i in range(0,__pieces__):
        h.piece_priority( piece_set[i], 7 )
    for i in range(__pieces__,__pieces__*2):
        h.piece_priority( piece_set[i], 6 )
    for i in range(__pieces__*2,__pieces__*3):
        h.piece_priority( piece_set[i], 5 )
    for i in range(len(piece_set)-__pieces__,len(piece_set)):
        h.piece_priority( piece_set[i], 7 )

    if _log:
        print "#### h.file_priorities() ## %s ##" % h.file_priorities()
        print "#### h.piece_priorities() ## %s ##" % h.piece_priorities()

    return piece_set

#!/usr/bin/perl
use strict;
use warnings;
use LWP::UserAgent;
use URI;
use HTML::TreeBuilder;
use Tk;
use threads;
use threads::shared;

# Lista de agentes de usuario
my @userAgents = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/58.0.3039.10 Safari/537.3',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) HeadlessChrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebkit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:42.0) Gecko/20100101 Firefox/42.0',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:39.0) Gecko/20100101 Firefox/39.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36 Edge/74.0.1371.47',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.119 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:36.0) Gecko/20100101 Firefox/36.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:85.0) Gecko/20100101 Firefox/85.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:85.0) Gecko/20100101 Firefox/85.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
);

# Lista de proxies (puedes usar un servicio de proxies rotativos)
my @proxies = (
    'http://proxy1:port',
    'http://proxy2:port',
    # Añade más proxies aquí
);

# Función para seleccionar un proxy aleatorio
sub select_proxy {
    return $proxies[rand @proxies] if @proxies;
    return undef;
}

# Función para rotar los proxies
sub rotate_proxies {
    push @proxies, shift @proxies if @proxies;
}

# Función para obtener el contenido de una URL con reintentos, proxies y delay aleatorio
sub fetch_url {
    my ($url, $retries) = @_;
    $retries //= 3;

    my $ua = LWP::UserAgent->new;
    $ua->agent($userAgents[rand @userAgents]);
    $ua->timeout(10);

    my $proxy = select_proxy();
    $ua->proxy(['http', 'https'], $proxy) if $proxy;

    for my $attempt (1 .. $retries) {
        sleep(int(rand(3)) + 1);  # Delay aleatorio entre solicitudes
        my $response = $ua->get($url);

        if ($response->is_success) {
            # Detectar CAPTCHA en la respuesta
            if ($response->content =~ /captcha/i) {
                warn "CAPTCHA detectado en $url. Pausando el scraping.\n";
                return undef;
            }
            return $response->content;
        } else {
            warn "Intento $attempt fallido para $url: " . $response->status_line . "\n";
            rotate_proxies();
            $proxy = select_proxy();
            $ua->proxy(['http', 'https'], $proxy) if $proxy;
            sleep(2 ** $attempt);  # Espera exponencial
        }
    }
    warn "No se pudo acceder a $url después de $retries intentos\n";
    return undef;
}

# Función para extraer URLs de una página
sub extract_urls_from_page {
    my ($url, $base_url) = @_;
    my $html_content = fetch_url($url);
    return () unless $html_content;

    my $tree = HTML::TreeBuilder->new_from_content($html_content);
    my @urls;
    for my $link ($tree->look_down(_tag => 'a', href => qr/.+/)) {
        my $full_url = URI->new_abs($link->attr('href'), $base_url)->as_string;
        push @urls, $full_url;
    }
    $tree->delete;
    return @urls;
}

# Función para clasificar URLs multimedia
sub extract_multimedia {
    my ($url) = @_;
    my $html_content = fetch_url($url);
    return {} unless $html_content;

    my $tree = HTML::TreeBuilder->new_from_content($html_content);
    my %recursos = (
        imagenes  => [],
        videos    => [],
        audios    => [],
        documentos => [],
        otros     => [],
    );

    for my $tag ($tree->look_down(_tag => qr/^(img|a|video|audio|source)$/)) {
        my $recurso_url = $tag->attr('src') || $tag->attr('href');
        next unless $recurso_url;

        if ($recurso_url =~ /\.(jpg|jpeg|png|gif|svg)$/i) {
            push @{$recursos{imagenes}}, $recurso_url;
        } elsif ($recurso_url =~ /\.(mp4|webm|avi)$/i) {
            push @{$recursos{videos}}, $recurso_url;
        } elsif ($recurso_url =~ /\.(mp3|wav|ogg)$/i) {
            push @{$recursos{audios}}, $recurso_url;
        } elsif ($recurso_url =~ /\.(pdf|docx|txt)$/i) {
            push @{$recursos{documentos}}, $recurso_url;
        } else {
            push @{$recursos{otros}}, $recurso_url;
        }
    }
    $tree->delete;
    return \%recursos;
}

# Función para indexar URLs por niveles
sub index_urls_by_level {
    my ($start_url, $max_level) = @_;
    my %visited : shared;
    my @to_visit = ([$start_url, 0]);
    my @all_urls;
    my @all_multimedia;

    while (@to_visit) {
        my ($current_url, $current_level) = @{shift @to_visit};
        next if $visited{$current_url} || $current_level > $max_level;
        $visited{$current_url} = 1;
        push @all_urls, $current_url;

        print "Nivel $current_level: Indexando $current_url\n";

        # Extraer URLs de la página actual
        my @new_urls = extract_urls_from_page($current_url, $start_url);
        for my $new_url (@new_urls) {
            push @to_visit, [$new_url, $current_level + 1] unless $visited{$new_url};
        }

        # Extraer multimedia de la página actual
        my $multimedia = extract_multimedia($current_url);
        if ($multimedia) {
            push @all_multimedia, [$current_url, $multimedia];
            print "Recursos multimedia en $current_url:\n";
            for my $tipo (keys %$multimedia) {
                if (@{$multimedia->{$tipo}}) {
                    print "  $tipo:\n";
                    for my $recurso (@{$multimedia->{$tipo}}) {
                        print "    - $recurso\n";
                    }
                }
            }
        }
    }
    return (\@all_urls, \@all_multimedia);
}

# Función para guardar resultados en archivos
sub save_results {
    my ($urls, $multimedia) = @_;
    my $carpeta_usuario = $ENV{HOME};
    my $ruta_resultados = "$carpeta_usuario/resultados";
    mkdir $ruta_resultados unless -d $ruta_resultados;

    # Guardar URLs indexadas
    open my $fh_urls, '>', "$ruta_resultados/urls_indexadas.txt" or die $!;
    print $fh_urls join("\n", @$urls), "\n";
    close $fh_urls;

    # Guardar recursos multimedia
    open my $fh_multimedia, '>', "$ruta_resultados/multimedia.txt" or die $!;
    for my $item (@$multimedia) {
        my ($url, $recursos) = @$item;
        print $fh_multimedia "Recursos multimedia en $url:\n";
        for my $tipo (keys %$recursos) {
            if (@{$recursos->{$tipo}}) {
                print $fh_multimedia "  $tipo:\n";
                for my $recurso (@{$recursos->{$tipo}}) {
                    print $fh_multimedia "    - $recurso\n";
                }
            }
        }
    }
    close $fh_multimedia;
}

# Interfaz gráfica con Tk
sub create_gui {
    my $root = MainWindow->new;
    $root->title("BunkerWallx Scraper");
    $root->geometry("600x400");

    # Etiquetas y campos de entrada
    $root->Label(-text => "URL de la página:")->grid(-row => 0, -column => 0, -padx => 10, -pady => 10);
    my $url_entry = $root->Entry(-width => 50);
    $url_entry->grid(-row => 0, -column => 1, -padx => 10, -pady => 10);

    $root->Label(-text => "Nivel de indexación:")->grid(-row => 1, -column => 0, -padx => 10, -pady => 10);
    my $level_entry = $root->Entry(-width => 10);
    $level_entry->grid(-row => 1, -column => 1, -padx => 10, -pady => 10);

    # Botón de inicio
    my $start_button = $root->Button(
        -text => "Iniciar Scraping",
        -command => sub {
            my $url = $url_entry->get;
            my $max_level = $level_entry->get;

            unless ($url && $max_level =~ /^\d+$/ && $max_level >= 0) {
                $root->messageBox(-type => 'ok', -icon => 'error', -message => "Por favor, ingresa una URL válida y un nivel de indexación mayor o igual a 0.");
                return;
            }

            my $result_text = $root->Scrolled('Text', -width => 70, -height => 15);
            $result_text->grid(-row => 3, -column => 0, -columnspan => 2, -padx => 10, -pady => 10);
            $result_text->insert('end', "Iniciando scraping...\n");
            $root->update;

            my ($indexed_urls, $multimedia) = index_urls_by_level($url, $max_level);
            save_results($indexed_urls, $multimedia);

            $result_text->insert('end', "Tiempo total de ejecución: " . time . " segundos\n");
            $result_text->insert('end', "Total de URLs indexadas: " . scalar @$indexed_urls . "\n");
            $result_text->insert('end', "Resultados guardados en ~/resultados/\n");
        }
    );
    $start_button->grid(-row => 2, -column => 0, -columnspan => 2, -pady => 20);

    MainLoop;
}

# Ejecución de la aplicación
create_gui();

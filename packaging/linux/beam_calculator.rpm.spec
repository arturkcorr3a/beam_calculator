# RPM of the app folder that PyInstaller already built (dist/beam_calculator/).
# Built by packaging/build_rpm.sh, which passes app_version, repo_dir and app_dir.

# The folder is a finished PyInstaller bundle: no debug package, and none of the
# post-install steps that strip, byte-compile or check its bundled libraries
%global debug_package %{nil}
%global __os_install_post %{nil}
%global __arch_install_post %{nil}

Name:           beam_calculator
Version:        %{app_version}
Release:        1%{?dist}
Summary:        Dimensionamento de vigas em concreto armado
# The app's own license; the bundled packages' (LGPL-3.0, BSD, MIT, PSF, Apache)
# are in /opt/beam_calculator/_internal/licenses/
License:        GPL-3.0-or-later
BuildArch:      x86_64

# Its libraries come bundled, so their automatic requirements would only ask for
# what is already inside. These are the ones PyInstaller leaves to the system
# (graphics drivers and Wayland), found by ldd in a clean Fedora container
AutoReqProv:    no
Requires:       libEGL.so.1()(64bit)
Requires:       libGL.so.1()(64bit)
Requires:       libdrm.so.2()(64bit)
Requires:       libwayland-client.so.0()(64bit)
Requires:       libwayland-cursor.so.0()(64bit)
Requires:       libwayland-egl.so.1()(64bit)
Requires:       fontconfig
Requires:       hicolor-icon-theme

%description
beam_calculator: projeto de vigas de concreto armado de um pavimento,
conforme a ABNT NBR 6118. Trabalho de Conclusão de Curso (UFRGS).

%install
mkdir -p %{buildroot}/opt %{buildroot}%{_bindir}
cp -a %{app_dir} %{buildroot}/opt/beam_calculator
# Only for the .tar.gz: the RPM installs the menu entry itself
rm -f %{buildroot}/opt/beam_calculator/install.sh %{buildroot}/opt/beam_calculator/beam_calculator.desktop
ln -s /opt/beam_calculator/beam_calculator %{buildroot}%{_bindir}/beam_calculator
install -Dm 644 %{repo_dir}/LICENSE %{buildroot}%{_licensedir}/%{name}/LICENSE

install -Dm 644 %{repo_dir}/packaging/linux/beam_calculator.desktop \
    %{buildroot}%{_datadir}/applications/beam_calculator.desktop
icons=%{repo_dir}/resources/logo
for size in 16 32 48; do
    install -Dm 644 $icons/png/icon/favicon-$size.png \
        %{buildroot}%{_datadir}/icons/hicolor/${size}x${size}/apps/beam_calculator.png
done
install -Dm 644 $icons/png/icon/beam-app-icon-512.png \
    %{buildroot}%{_datadir}/icons/hicolor/512x512/apps/beam_calculator.png
install -Dm 644 $icons/svg/icon/beam-app-icon.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/beam_calculator.svg

%files
%license %{_licensedir}/%{name}/LICENSE
/opt/beam_calculator
%{_bindir}/beam_calculator
%{_datadir}/applications/beam_calculator.desktop
%{_datadir}/icons/hicolor/*/apps/beam_calculator.*

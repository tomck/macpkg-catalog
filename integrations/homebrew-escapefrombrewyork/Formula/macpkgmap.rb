class Macpkgmap < Formula
  desc "Neutral catalog of macOS packages and cross-manager relationships"
  homepage "https://github.com/tomck/macpkg-catalog"
  url "https://github.com/tomck/macpkg-catalog/archive/refs/tags/macpkgmap-v0.1.0.tar.gz"
  sha256 "665dbb3b97d1e87f430f009c0d48610ccc8aa43c7c1bf051c0057f019be7a4a1"
  license "MIT"
  depends_on "python@3.14"

  def install
    libexec.install "macpkg_catalog"
    (bin/"macpkgmap").write <<~EOS
      #!/bin/sh
      export PYTHONPATH="#{libexec}${PYTHONPATH:+:$PYTHONPATH}"
      exec "#{Formula["python@3.14"].opt_bin}/python3.14" -m macpkg_catalog "$@"
    EOS
    chmod 0755, bin/"macpkgmap"
  end

  test do
    system bin/"macpkgmap", "--help"
  end
end

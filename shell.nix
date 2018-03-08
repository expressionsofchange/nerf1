with import <nixpkgs> {};

(pkgs.python35.withPackages (ps: [ps.kivy])).env
